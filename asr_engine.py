"""ASR engine: Gemini API (primary) with local mlx-qwen3-asr as fallback.

If GEMINI_API_KEY is set in the environment, Gemini API is used for transcription.
Otherwise, the local Qwen3-ASR model is used automatically.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from config import (
    AUDIO_SAMPLE_RATE,
    FFMPEG_BIN,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


# ─────────────────────────── Shared utilities ────────────────────────────────

def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def _get_media_duration_sec(path: Path) -> float:
    """Return duration in seconds via ffprobe; 0 if unavailable."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return 0.0


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract full audio from video to 16kHz mono WAV."""
    audio_path = output_dir / f"{video_path.stem}.wav"
    if audio_path.exists():
        dur = _get_media_duration_sec(audio_path)
        if dur > 0:
            print(f"  [skip] Audio already extracted: {audio_path.name} ({dur / 60:.1f} min)")
        else:
            print(f"  [skip] Audio already extracted: {audio_path.name}")
        return audio_path

    cmd = [
        FFMPEG_BIN, "-i", str(video_path),
        "-map", "0:a:0",
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "1",
        "-y",
        str(audio_path),
    ]
    print(f"  Extracting audio: {video_path.name} -> {audio_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        cmd_fallback = [
            FFMPEG_BIN, "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le",
            "-ar", str(AUDIO_SAMPLE_RATE), "-ac", "1", "-y", str(audio_path),
        ]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    dur = _get_media_duration_sec(audio_path)
    if dur > 0:
        print(f"  Extracted duration: {dur / 60:.1f} min")
    return audio_path


# ─────────────────────────── Gemini ASR ─────────────────────────────────────

_GEMINI_ASR_SYSTEM_PROMPT = """\
You are a professional transcription service. Transcribe the audio file provided.

Output ONLY a valid SRT subtitle file. Rules:
- Each entry must have: index number, timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm), and text.
- Timestamps must be accurate to the audio.
- Each subtitle should be 1-2 sentences, roughly 5-10 seconds long.
- Do NOT include any explanation, preamble, or code fences.
- Do NOT translate — output the original language only.
- Preserve proper nouns, abbreviations, and technical terms exactly as spoken.

Example format:
1
00:00:00,000 --> 00:00:05,200
Hello, this is the first subtitle.

2
00:00:05,500 --> 00:00:10,800
And this is the second one.
"""


_MIME_TYPES: dict[str, str] = {
    # Video
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4v": "video/mp4",
    ".ts": "video/mp2t",
    # Audio
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
}


def _transcribe_with_gemini(
    media_path: Path,
    language: str | None,
    model: str = "gemini-2.5-flash",
) -> str:
    """Upload media file (video or audio) to Gemini and return raw SRT string."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)

    mime_type = _MIME_TYPES.get(media_path.suffix.lower(), "video/mp4")
    print(f"  Uploading to Gemini Files API: {media_path.name} ({mime_type})")
    t0 = time.time()
    uploaded_file = client.files.upload(
        file=media_path,
        config={"mime_type": mime_type},
    )
    print(f"  Upload done in {time.time() - t0:.1f}s. Processing...")

    lang_instruction = ""
    if language:
        lang_instruction = f"\nThe audio language is {language}. Transcribe in {language}."

    prompt = _GEMINI_ASR_SYSTEM_PROMPT + lang_instruction

    # Poll until file is ACTIVE (processing can take a moment for large files)
    while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
        time.sleep(3)
        uploaded_file = client.files.get(name=uploaded_file.name)

    t1 = time.time()
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_uri(
                file_uri=uploaded_file.uri,
                mime_type=uploaded_file.mime_type,
            ),
            types.Part.from_text(text=prompt),
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
        ),
    )
    print(f"  Transcription done in {time.time() - t1:.1f}s")

    # Clean up uploaded file to free quota
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return response.text


def _parse_gemini_srt_to_entries(raw_srt: str) -> list[dict]:
    """Convert raw SRT string to list of segment dicts compatible with write_srt."""
    # Strip any markdown code fences if present
    raw_srt = re.sub(r"^```[^\n]*\n", "", raw_srt.strip(), flags=re.MULTILINE)
    raw_srt = re.sub(r"```$", "", raw_srt.strip())
    return raw_srt.strip()


# ─────────────────────────── Local ASR (fallback) ────────────────────────────

def _collapse_repeated_chars(text: str) -> str:
    """Collapse repeated characters like 我我我我 -> 我."""
    if not text:
        return text
    return re.sub(r"(.)\1+", r"\1", text)


class _CleanedResult:
    """Compatible result object for write_txt / write_srt."""
    def __init__(self, text, language, segments=None, chunks=None, speaker_segments=None):
        self.text = text
        self.language = language
        self.segments = segments
        self.chunks = chunks
        self.speaker_segments = speaker_segments


def _clean_transcript_result(result) -> _CleanedResult:
    cleaned_text = _collapse_repeated_chars(result.text)
    cleaned_segments = None
    if result.segments:
        cleaned_segments = [
            {**seg, "text": _collapse_repeated_chars(seg.get("text", ""))}
            for seg in result.segments
        ]
    cleaned_chunks = None
    if result.chunks:
        cleaned_chunks = [
            {**c, "text": _collapse_repeated_chars(c.get("text", ""))}
            for c in result.chunks
        ]
    cleaned_speaker = None
    if result.speaker_segments:
        cleaned_speaker = [
            {**s, "text": _collapse_repeated_chars(s.get("text", ""))}
            for s in result.speaker_segments
        ]
    return _CleanedResult(
        text=cleaned_text,
        language=result.language,
        segments=cleaned_segments,
        chunks=cleaned_chunks,
        speaker_segments=cleaned_speaker,
    )


def _transcribe_with_local_model(
    media_files: list[Path],
    language: str | None,
    transcript_only: bool,
) -> dict[Path, Path]:
    """Transcribe using local mlx-qwen3-asr model."""
    from config import ASR_MODEL, ASR_MAX_NEW_TOKENS
    from mlx_qwen3_asr import Session
    from mlx_qwen3_asr.writers import write_srt, write_txt

    print(f"\n{'='*60}")
    print(f"Loading local ASR model: {ASR_MODEL}")
    print(f"{'='*60}")
    t0 = time.time()
    session = Session(model=ASR_MODEL)
    print(f"Model loaded in {time.time() - t0:.1f}s\n")

    results: dict[Path, Path] = {}

    for i, media_path in enumerate(media_files, 1):
        print(f"[{i}/{len(media_files)}] Processing: {media_path.name}")
        src_dur = _get_media_duration_sec(media_path)
        if src_dur > 0:
            print(f"  Source duration: {src_dur / 60:.1f} min")
        out_dir = OUTPUT_DIR / media_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            if media_path.suffix.lower() in AUDIO_EXTENSIONS:
                audio_path = media_path
            else:
                audio_path = extract_audio(media_path, out_dir)

            txt_path = out_dir / f"{media_path.stem}.txt"
            srt_path = out_dir / f"{media_path.stem}.srt"

            print(f"  Transcribing ({language or 'auto-detect'})...")
            t1 = time.time()
            result = session.transcribe(
                str(audio_path),
                language=language,
                return_timestamps=not transcript_only,
                verbose=True,
                max_new_tokens=ASR_MAX_NEW_TOKENS,
            )
            elapsed = time.time() - t1
            print(f"  Language: {result.language}")
            print(f"  Transcription done in {elapsed:.1f}s")

            cleaned = _clean_transcript_result(result)
            if transcript_only:
                write_txt(cleaned, str(txt_path))
                print(f"  Saved: {txt_path.name}")
                results[media_path] = txt_path
            else:
                write_srt(cleaned, str(srt_path))
                print(f"  Saved: {srt_path.name}")
                write_txt(cleaned, str(txt_path))
                print(f"  Saved: {txt_path.name}")
                results[media_path] = srt_path

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")

    return results


# ─────────────────────────── Public API ─────────────────────────────────────

def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
    transcript_only: bool = False,
) -> dict[Path, Path]:
    """Transcribe media files. Uses Gemini API if GEMINI_API_KEY is set,
    otherwise falls back to local mlx-qwen3-asr model.

    Returns: {media_path: srt_path or txt_path}
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if gemini_key:
        return _transcribe_files_gemini(media_files, language, transcript_only)
    else:
        print("GEMINI_API_KEY not set — using local ASR model as fallback.")
        return _transcribe_with_local_model(media_files, language, transcript_only)


def _transcribe_files_gemini(
    media_files: list[Path],
    language: str | None,
    transcript_only: bool,
) -> dict[Path, Path]:
    """Transcribe using Gemini API and write SRT + TXT files."""
    from srt_utils import parse_srt, write_srt, SrtEntry

    gemini_model = os.environ.get("GEMINI_ASR_MODEL", "gemini-2.5-flash")

    print(f"\n{'='*60}")
    print(f"ASR backend: Google Gemini API ({gemini_model})")
    print(f"{'='*60}\n")

    results: dict[Path, Path] = {}

    for i, media_path in enumerate(media_files, 1):
        print(f"[{i}/{len(media_files)}] Processing: {media_path.name}")
        src_dur = _get_media_duration_sec(media_path)
        if src_dur > 0:
            print(f"  Source duration: {src_dur / 60:.1f} min")

        out_dir = OUTPUT_DIR / media_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        srt_path = out_dir / f"{media_path.stem}.srt"
        txt_path = out_dir / f"{media_path.stem}.txt"

        # Check if SRT already exists (skip ASR)
        if srt_path.exists() and not transcript_only:
            print(f"  [skip] SRT already exists: {srt_path.name}")
            results[media_path] = srt_path
            continue

        try:
            # Upload the original media file directly to Gemini (no WAV conversion needed)
            # For already-audio files, upload as-is; for video files, upload MP4 directly
            raw_srt = _transcribe_with_gemini(media_path, language, gemini_model)

            if transcript_only:
                # Parse SRT and write only TXT
                entries = parse_srt(raw_srt)
                plain_text = " ".join(e.text for e in entries)
                txt_path.write_text(plain_text + "\n", encoding="utf-8")
                print(f"  Saved: {txt_path.name}")
                results[media_path] = txt_path
            else:
                # Write full SRT file
                srt_path.write_text(raw_srt, encoding="utf-8")
                print(f"  Saved: {srt_path.name}")

                # Also write plain TXT
                entries = parse_srt(raw_srt)
                plain_text = " ".join(e.text for e in entries)
                txt_path.write_text(plain_text + "\n", encoding="utf-8")
                print(f"  Saved: {txt_path.name}")

                results[media_path] = srt_path

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")

    return results
