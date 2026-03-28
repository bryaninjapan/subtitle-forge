"""ASR engine using Gemini API for video/audio transcription."""

from __future__ import annotations

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from usage_tracker import log_usage  # type: ignore
from media_utils import get_media_duration_sec  # type: ignore
from gemini_client import get_gemini_client  # type: ignore

from config import (
    AUDIO_SAMPLE_RATE,
    DEFAULT_GEMINI_MODEL,
    FFMPEG_BIN,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)  # type: ignore

# ─────────────────────────── Shared utilities ────────────────────────────────

def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

def _get_gemini_client():
    return get_gemini_client()

def check_dependencies() -> None:
    """Ensure ffmpeg and ffprobe are installed and available."""
    from config import FFMPEG_BIN  # type: ignore
    for tool in [FFMPEG_BIN, "ffprobe"]:
        try:
            subprocess.run([tool, "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"\n[CRITICAL ERROR] '{tool}' not found!")
            print(f"Subtitle Forge requires {tool} to process video and audio.")
            print("Please install ffmpeg (e.g., 'brew install ffmpeg' on macOS).")
            sys.exit(1)
    print("  [Init] Dependencies check passed: ffmpeg/ffprobe found.")

def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract full audio from video to 16kHz mono WAV."""
    audio_path = output_dir / f"{video_path.stem}.wav"
    if audio_path.exists():
        dur = get_media_duration_sec(audio_path)
        if dur > 0:
            print(f"  [skip] Audio already extracted: {audio_path.name} ({dur / 60:.1f} min)")
        return audio_path

    cmd = [
        FFMPEG_BIN, "-i", str(video_path),
        "-vn",
        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample={AUDIO_SAMPLE_RATE}",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-y",
        str(audio_path),
    ]
    print(f"  Extracting & Denoising audio: {video_path.name} -> {audio_path.name}")
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
    
    if audio_path.stat().st_size < 1000:
        raise RuntimeError(f"Extracted audio is too small. Ffmpeg might have failed.")
    return audio_path

def check_silence(audio_path: Path, threshold_db: int = -40) -> bool:
    """Check if the audio file is mostly silent."""
    from config import FFMPEG_BIN  # type: ignore
    duration = get_media_duration_sec(audio_path)
    if duration <= 0: return True
    cmd = [FFMPEG_BIN, "-i", str(audio_path), "-af", f"silencedetect=n={threshold_db}dB:d=2", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    import re
    silence_durations = re.findall(r"silence_duration: ([\d\.]+)", result.stderr)
    total_silence = sum(float(d) for d in silence_durations)
    return (total_silence / duration) > 0.95

# ─────────────────────────── Gemini ASR ─────────────────────────────────────

_GEMINI_ASR_SYSTEM_PROMPT = """\
You are a professional transcription service. Transcribe the audio file provided.
Output ONLY a valid SRT subtitle file. Follow this EXACT format:

1
00:00:01,000 --> 00:00:05,500
First subtitle text here.

2
00:00:06,000 --> 00:00:11,200
Second subtitle text here.

STRICT FORMAT RULES:
- Index number and timestamp MUST be on SEPARATE lines. Never on the same line.
- Timestamp format is EXACTLY: HH:MM:SS,mmm --> HH:MM:SS,mmm
  - HH = 2-digit hours (always include, use 00 if less than 1 hour)
  - MM = 2-digit minutes
  - SS = 2-digit seconds
  - mmm = 3-digit milliseconds
  - Separator before milliseconds is a COMMA (,) NOT a colon (:)
  - CORRECT: 00:01:23,456 --> 00:01:27,890
  - WRONG:   00:01:23:456  (colon before ms)
  - WRONG:   1 00:01:23,456 (index on same line as timestamp)
- Each subtitle: 1-2 sentences, roughly 5-10 seconds.
- Do NOT include any explanation, preamble, or code fences.
- Do NOT translate — output the original language only.
- Preserve proper nouns, abbreviations, and technical terms exactly as spoken.
- Speaker Diarization: If multiple speakers are detected, prefix lines with [Speaker A], [Speaker B], etc.
"""

def _transcribe_with_gemini(
    media_path: Path,
    language: str | None,
    model: str = DEFAULT_GEMINI_MODEL,
    retries: int = 3,
    retry_delay: float = 10.0,
) -> tuple[str, object]:  # type: ignore
    from google.genai import types  # type: ignore
    from usage_tracker import signal_backoff  # type: ignore
    from config import MIME_TYPES, get_truncated_glossary  # type: ignore

    client = _get_gemini_client()
    mime_type = MIME_TYPES.get(media_path.suffix.lower(), "video/mp4")

    uploaded_file = None
    try:
        for attempt in range(1, retries + 1):
            try:
                print(f"  Uploading to Gemini (attempt {attempt}): {media_path.name}...")
                uploaded_file = client.files.upload(file=str(media_path), config={"mime_type": mime_type})
                break
            except Exception as e:
                if attempt == retries:
                    from usage_tracker import log_failure  # type: ignore  # type: ignore
                    log_failure("ASR Upload", media_path.name, str(e))
                    raise
                time.sleep(retry_delay)

        if not uploaded_file:
            raise RuntimeError("Failed to obtain uploaded_file from Gemini API")
            
        while uploaded_file.state.name == "PROCESSING":  # type: ignore
            time.sleep(5)
            uploaded_file = client.files.get(name=uploaded_file.name)  # type: ignore

        lang_instr = f"\nThe audio language is {language}. Transcribe in {language}." if language else ""
        glossary = get_truncated_glossary(50) # Use top 50 terms to keep focus
        gloss_instr = f"\n\nTechnical context:\n" + ", ".join(f"{k}({v})" for k,v in glossary.items()) if glossary else ""
        prompt = _GEMINI_ASR_SYSTEM_PROMPT + lang_instr + gloss_instr

        import random
        for attempt in range(1, retries + 1):
            try:
                from usage_tracker import check_backoff, signal_backoff  # type: ignore
                check_backoff()
                response = client.models.generate_content(
                    model=model,
                    contents=[types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type)],  # type: ignore
                    config=types.GenerateContentConfig(system_instruction=prompt, temperature=0.0),
                )
                return response.text, response.usage_metadata
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in ["429", "quota", "overloaded", "503"]):
                    wait = (retry_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
                    signal_backoff(wait + 5)
                    time.sleep(wait)
                elif attempt == retries:
                    raise
        raise RuntimeError("ASR failed after retries")
    finally:
        if uploaded_file:
            try: client.files.delete(name=uploaded_file.name)  # type: ignore
            except: pass

# ─────────────────────────── Public API ─────────────────────────────────────

def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
    dry_run: bool = False,
) -> dict[Path, Path]:
    from srt_utils import parse_srt, clean_subtitle_text, write_srt  # type: ignore
    gemini_model = str(os.environ.get("GEMINI_ASR_MODEL", DEFAULT_GEMINI_MODEL))

    print(f"\n{'='*60}")
    print(f"ASR backend: Google Gemini API ({gemini_model}) {'[DRY RUN]' if dry_run else ''}")
    print(f"{'='*60}\n")

    results: dict[Path, Path] = {}

    for i, media_path in enumerate(media_files, 1):
        print(f"[{i}/{len(media_files)}] Processing: {media_path.name}")
        out_dir = OUTPUT_DIR / media_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        srt_path = out_dir / f"{media_path.stem}.srt"

        if srt_path.exists():
            print(f"  [skip] SRT already exists")
            results[media_path] = srt_path
            continue

        if dry_run:
            print(f"  [dry-run] Would transcribe {media_path.name}")
            results[media_path] = srt_path
            continue

        try:
            upload_path = media_path
            if media_path.suffix.lower() in VIDEO_EXTENSIONS:
                upload_path = extract_audio(media_path, out_dir)

            # Silence cache with stats check
            stats = f"{upload_path.stat().st_size}_{upload_path.stat().st_mtime}"
            silence_cache = out_dir / ".silence_cached"
            if silence_cache.exists() and silence_cache.read_text(encoding="utf-8") == stats:
                print(f"  [skip] Silence check cached.")
            else:
                # The original line was 'from config import SILENCE_THRESHOLD'.
                # The user's requested change 'from config import SILENCE_THRESHOLD = -50' is a syntax error.
                # To achieve the apparent intent of setting SILENCE_THRESHOLD to -50,
                # we define it locally here.
                SILENCE_THRESHOLD = -50  # dB - raised to avoid false-positive silent detection
                if check_silence(upload_path, threshold_db=SILENCE_THRESHOLD):
                    from usage_tracker import log_failure  # type: ignore
                    log_failure("ASR", media_path.name, "Audio is mostly silent, skipping transcription")
                    print(f"  [skip] Mostly silent.")
                    continue
                silence_cache.write_text(stats, encoding="utf-8")

            raw_srt, usage = _transcribe_with_gemini(upload_path, language, gemini_model)
            if usage:
                log_usage("ASR", media_path.name, usage.prompt_token_count, usage.candidates_token_count)  # type: ignore

            if not raw_srt.strip():
                from usage_tracker import log_failure  # type: ignore
                log_failure("ASR", media_path.name, "Gemini returned empty transcription")
                print(f"  [WARNING] Gemini returned EMPTY transcription for {media_path.name}.")
                (out_dir / f"{media_path.stem}_asr_debug.txt").write_text("[EMPTY RESPONSE]", encoding="utf-8")
                continue

            entries = parse_srt(raw_srt)
            if not entries:
                from usage_tracker import log_failure  # type: ignore
                debug_p = out_dir / f"{media_path.stem}_asr_debug.txt"
                debug_p.write_text(raw_srt, encoding="utf-8")
                log_failure("ASR", media_path.name, f"Could not parse SRT format. First 200 chars: {raw_srt[:200]}")  # type: ignore
                print(f"  [WARNING] Could not parse SRT format. Raw response saved to {debug_p.name}")
                txt_path = out_dir / f"{media_path.stem}.transcript.txt"
                txt_path.write_text(raw_srt, encoding="utf-8")
                continue

            # Clean ONLY cosmetic noise - preserve speaker tags
            for e in entries:
                e.text = clean_subtitle_text(e.text)
            # Remove any entries that ended up empty after cleaning
            entries = [e for e in entries if e.text]
            if not entries:
                from usage_tracker import log_failure  # type: ignore
                log_failure("ASR", media_path.name, "All subtitle entries were empty after cleaning")
                print(f"  [ERROR] All entries were empty after cleaning for {media_path.name}")
                continue

            # Sanity-check: flag suspiciously low entry density (e.g. whole transcript
            # in one block).  Minimum 1 entry per 2 minutes for any video > 5 min.
            duration_sec = get_media_duration_sec(upload_path)
            if duration_sec > 300:
                min_expected = max(5, int(duration_sec / 120))
                if len(entries) < min_expected:
                    from usage_tracker import log_failure  # type: ignore
                    log_failure("ASR", media_path.name,
                                f"Suspicious output: {len(entries)} entries for "
                                f"{duration_sec/60:.1f}min audio (expected ≥{min_expected}). "
                                "Gemini may have returned garbled SRT format.")
                    print(f"  [WARNING] Only {len(entries)} entries for "
                          f"{duration_sec/60:.1f}min audio — ASR output may be garbled.")

            write_srt(entries, srt_path)
            txt_path = out_dir / f"{media_path.stem}.transcript.txt"
            txt_path.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")
            
            # Clean up extracted audio
            if upload_path != media_path and upload_path.exists():
                try: upload_path.unlink()
                except: pass
                
            results[media_path] = srt_path
            print(f"  Saved: {srt_path.name} ({len(entries)} entries)")
        except Exception as e:
            from usage_tracker import log_failure  # type: ignore
            log_failure("ASR Pipeline", media_path.name, str(e))
            print(f"  [ERROR] {e}")

    return results

def transcribe_one_video(audio_16khz_path: str, language: Optional[str], working_directory: str) -> Dict[str, Any]:
    """Single-video ASR wrapper for the Multi-Agent Director."""
    from pathlib import Path
    a_p = Path(audio_16khz_path)
    w_d = Path(working_directory)
    
    # 1. Transcribe with AI (Gemini Flash)
    raw_srt, usage = _transcribe_with_gemini(a_p, language)
    
    # 2. Log usage if available
    if usage:
        from usage_tracker import log_usage # type: ignore
        log_usage("ASR", a_p.name, usage.prompt_token_count, usage.candidates_token_count)
    
    # 3. Clean and save result
    from srt_utils import parse_srt, clean_subtitle_text, write_srt # type: ignore
    entries = parse_srt(raw_srt)
    for e in entries:
        e.text = clean_subtitle_text(e.text)
        
    srt_p = w_d / f"{a_p.stem.replace('_16k', '')}.srt"
    write_srt(entries, srt_p)
    
    # 4. Save transcript preview
    txt_p = w_d / f"{srt_p.stem}.transcript.txt"
    txt_p.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")
    
    return {
        "raw_srt_text": raw_srt,
        "transcript_text": txt_p.read_text(encoding="utf-8"),
        "srt_path": str(srt_p)
    }

