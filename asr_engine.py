"""ASR engine using Gemini API for video/audio transcription."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from usage_tracker import log_usage

from config import (
    AUDIO_SAMPLE_RATE,
    DEFAULT_GEMINI_MODEL,
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


def check_dependencies() -> None:
    """Ensure ffmpeg and ffprobe are installed and available."""
    from config import FFMPEG_BIN
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
    
    # Check if file size is reasonable (not 0 bytes)
    if audio_path.stat().st_size < 1000:
        raise RuntimeError(f"Extracted audio file is too small ({audio_path.stat().st_size} bytes). Ffmpeg might have failed silently.")
        
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




def _transcribe_with_gemini(
    media_path: Path,
    language: str | None,
    model: str = "gemini-2.5-flash",
    retries: int = 3,
    retry_delay: float = 10.0,
) -> tuple[str, object]:
    """Upload media file to Gemini and return raw SRT string with retry logic."""
    from google import genai
    from google.genai import types
    from config import MIME_TYPES

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)
    mime_type = MIME_TYPES.get(media_path.suffix.lower(), "video/mp4")

    # 1. Upload with retry
    uploaded_file = None
    for attempt in range(1, retries + 1):
        try:
            print(f"  Uploading to Gemini (attempt {attempt}): {media_path.name}...")
            t0 = time.time()
            uploaded_file = client.files.upload(
                file=media_path,
                config={"mime_type": mime_type},
            )
            print(f"  Upload successful ({time.time() - t0:.1f}s). Waiting for processing...", end="", flush=True)
            break
        except Exception as e:
            if attempt < retries:
                print(f"  [retry {attempt}] Upload failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise

    # 2. Wait for ACTIVE state
    while uploaded_file.state and uploaded_file.state.name == "PROCESSING":
        time.sleep(5)
        print(".", end="", flush=True)
        uploaded_file = client.files.get(name=uploaded_file.name)
    print(" Done.")

    # 3. Request transcription with retry
    lang_instruction = ""
    if language:
        lang_instruction = f"\nThe audio language is {language}. Transcribe in {language}."
    
    # Add glossary context if available
    from config import load_glossary
    glossary = load_glossary()
    glossary_context = ""
    if glossary:
        terms = ", ".join(f"{k} ({v})" for k, v in glossary.items())
        glossary_context = f"\n\nContext & Technical Terms to recognize:\n{terms}"
        
    prompt = _GEMINI_ASR_SYSTEM_PROMPT + lang_instruction + glossary_context

    for attempt in range(1, retries + 1):
        try:
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
                config=types.GenerateContentConfig(temperature=0.0),
            )
            print(f"  Transcription done in {time.time() - t1:.1f}s")
            
            # Clean up
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
                
            return response.text, response.usage_metadata
        except Exception as e:
            if attempt < retries:
                print(f"  [retry {attempt}] Generation failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # Still try to delete if possible
                try: client.files.delete(name=uploaded_file.name)
                except: pass
                raise


# ─────────────────────────── Public API ─────────────────────────────────────

def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
) -> dict[Path, Path]:
    """Transcribe media files using Gemini API.

    Returns: {media_path: srt_path}
    """
    from srt_utils import parse_srt

    gemini_model = os.environ.get("GEMINI_ASR_MODEL", DEFAULT_GEMINI_MODEL)

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

        if srt_path.exists():
            print(f"  [skip] SRT already exists: {srt_path.name}")
            results[media_path] = srt_path
            continue

        try:
            # Always extract audio for video files before uploading.
            # Audio uses ~1,920 tokens/min vs ~17,700 tokens/min for video (~9x savings).
            upload_path = media_path
            if media_path.suffix.lower() in VIDEO_EXTENSIONS:
                print(f"  [audio-only] Extracting audio to reduce token usage (~9x savings)...")
                upload_path = extract_audio(media_path, out_dir)

            raw_srt, usage_meta = _transcribe_with_gemini(upload_path, language, gemini_model)

            if usage_meta:
                log_usage("ASR", media_path.name, usage_meta.prompt_token_count, usage_meta.candidates_token_count)
                print(f"  Token Usage (ASR): Input={usage_meta.prompt_token_count}, Output={usage_meta.candidates_token_count}, Total={usage_meta.total_token_count}")

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
