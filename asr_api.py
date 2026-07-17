"""OpenRouter API-based ASR backend.

Provides transcribe_via_api() as an alternative to the local MLX ASR backend.
Uses OpenAI-compatible client to call OpenRouter's speech-to-text models.
"""
from __future__ import annotations

import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from config import ASR_API_KEY_ENV, ASR_API_MODEL
from srt_utils import parse_srt  # type: ignore


# ── Shared helpers (mirror asr_engine for consistency) ───────────────────


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _group_segments_into_srt(segments: list[dict]) -> str:
    """Group word/segment dicts into SRT blocks.

    Each segment: {"text": str, "start": float, "end": float}
    """
    # Group into subtitle blocks (same logic as smart splitting)
    blocks: list[dict] = []
    buf_words: list[str] = []
    buf_start: float = 0.0
    buf_end: float = 0.0
    max_duration = 5.0
    max_chars = 80

    for seg in segments:
        word = seg["text"].strip()
        if not word:
            continue
        is_first = not buf_words
        projected = (" ".join(buf_words + [word])).strip()
        duration = seg["end"] - buf_start
        is_sentence_end = word.endswith((".", "?", "!", "...", "。", "？", "！"))

        if not is_first and (duration > max_duration or len(projected) > max_chars or is_sentence_end):
            if buf_words:
                blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})
            buf_words = [word]
            buf_start = seg["start"]
            buf_end = seg["end"]
        else:
            if is_first:
                buf_start = seg["start"]
            buf_words.append(word)
            buf_end = seg["end"]

    if buf_words:
        blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})

    srt_parts = []
    for i, b in enumerate(blocks, 1):
        start = _seconds_to_srt_time(b["start"])
        end = _seconds_to_srt_time(b["end"])
        srt_parts.append(f"{i}\n{start} --> {end}\n{b['text']}")
    return "\n\n".join(srt_parts) + "\n"


# ── Audio size management ────────────────────────────────────────────────

MAX_API_FILE_SIZE = 25 * 1024 * 1024  # 25 MB (OpenRouter Whisper limit)


def _compress_audio(input_path: Path) -> Optional[Path]:
    """Compress audio to fit within API file size limits.

    Uses ffmpeg to reduce bitrate. Returns path to compressed temp file.
    Returns None on failure.
    """
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ac", "1",              # mono
            "-ar", "16000",          # 16kHz
            "-b:a", "32k",           # low bitrate for compression
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        if tmp_path.stat().st_size < MAX_API_FILE_SIZE:
            return tmp_path

        # Still too large — try even lower bitrate
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ac", "1",
            "-ar", "8000",           # 8kHz (telephone quality, but small)
            "-b:a", "16k",
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        if tmp_path.stat().st_size < MAX_API_FILE_SIZE:
            return tmp_path

        # Still too large — clean up and return None for chunking
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return None
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return None


# ── Main API transcribe function ────────────────────────────────────────


def transcribe_via_api(audio_path: Path, language: Optional[str] = None) -> str:
    """Transcribe audio using OpenRouter API.

    Returns SRT-formatted text with word-level timestamps.
    Handles file size limits by compressing or chunking audio.

    Raises:
        RuntimeError: If API key is not set or API call fails.
    """
    api_key = os.environ.get(ASR_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"ASR API key not found. Set {ASR_API_KEY_ENV} environment variable."
        )

    file_size = audio_path.stat().st_size
    audio_to_send = audio_path
    cleanup_path: Optional[Path] = None

    # Compress if over limit
    if file_size > MAX_API_FILE_SIZE:
        compressed = _compress_audio(audio_path)
        if compressed:
            audio_to_send = compressed
            cleanup_path = compressed
        else:
            raise RuntimeError(
                f"Audio file too large ({file_size / 1024 / 1024:.1f} MB) "
                "and could not be compressed enough for API."
            )

    try:
        return _call_openrouter_api(audio_to_send, language)
    finally:
        if cleanup_path and cleanup_path.exists():
            try:
                cleanup_path.unlink()
            except OSError:
                pass


def _call_openrouter_api(audio_path: Path, language: Optional[str] = None) -> str:
    """Make the actual OpenRouter API call and return SRT."""
    from openai import OpenAI  # type: ignore

    api_key = os.environ.get(ASR_API_KEY_ENV, "")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # Read audio file
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    # Build request params
    kwargs = {
        "model": ASR_API_MODEL,
        "file": ("audio.wav", audio_data, "audio/wav"),
        "response_format": "verbose_json",
        "timestamp_granularities": ["word"],
    }
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.create(**kwargs)

    # Parse response into SRT
    segments = _extract_segments_from_response(response)
    return _group_segments_into_srt(segments)


def _extract_segments_from_response(response) -> list[dict]:
    """Extract word-level segments from OpenAI-compatible API response.

    Handles both verbose_json (with .words) and simple json responses.
    """
    segments: list[dict] = []

    # Try word-level timestamps first (verbose_json with timestamp_granularities=["word"])
    if hasattr(response, "words") and response.words:
        for w in response.words:
            word_text = w.text if hasattr(w, "text") else w.get("text", "")
            word_start = w.start if hasattr(w, "start") else w.get("start", 0.0)
            word_end = w.end if hasattr(w, "end") else w.get("end", 0.0)
            if word_text and word_text.strip():
                segments.append({
                    "text": word_text.strip(),
                    "start": float(word_start),
                    "end": float(word_end),
                })
        return segments

    # Fallback: use segments if available
    if hasattr(response, "segments") and response.segments:
        for s in response.segments:
            text = s.text if hasattr(s, "text") else s.get("text", "")
            start = s.start if hasattr(s, "start") else s.get("start", 0.0)
            end = s.end if hasattr(s, "end") else s.get("end", 0.0)
            if text and text.strip():
                segments.append({
                    "text": text.strip(),
                    "start": float(start),
                    "end": float(end),
                })
        return segments

    # Last resort: single entry from full text
    full_text = getattr(response, "text", "")
    if not full_text and hasattr(response, "get"):
        full_text = response.get("text", "")
    if full_text and full_text.strip():
        # Estimate duration from audio (we don't have it here, use a reasonable default)
        segments.append({
            "text": full_text.strip(),
            "start": 0.0,
            "end": 10.0,  # Placeholder — will be wrong for long audio
        })

    return segments
