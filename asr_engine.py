"""ASR engine using local Qwen3-ASR-1.7B (via mlx-qwen3-asr) for transcription."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from media_utils import get_media_duration_sec  # type: ignore

from config import (
    AUDIO_SAMPLE_RATE,
    FFMPEG_BIN,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)  # type: ignore

QWEN3_ASR_MODEL = "Qwen/Qwen3-ASR-1.7B"

# ─────────────────────────── Shared utilities ────────────────────────────────

def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

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

# ─────────────────────────── Qwen3-ASR ──────────────────────────────────────

def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _group_words_into_subtitles(
    segments: list[dict],
    max_duration: float = 5.0,
    max_chars: int = 80,
) -> list[dict]:
    """Merge word-level segments into subtitle-sized blocks."""
    blocks: list[dict] = []
    buf_words: list[str] = []
    buf_start: float = 0.0
    buf_end: float = 0.0

    for seg in segments:
        word = seg["text"].strip()
        if not word:
            continue

        is_first = not buf_words
        projected_text = (" ".join(buf_words + [word])).strip()
        duration = seg["end"] - buf_start
        sentence_end = word.endswith((".", "?", "!", "...", "。", "？", "！"))

        if not is_first and (
            duration > max_duration
            or len(projected_text) > max_chars
        ):
            blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})
            buf_words = [word]
            buf_start = seg["start"]
            buf_end = seg["end"]
        else:
            if is_first:
                buf_start = seg["start"]
            buf_words.append(word)
            buf_end = seg["end"]

        if sentence_end and buf_words:
            blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})
            buf_words = []

    if buf_words:
        blocks.append({"text": " ".join(buf_words), "start": buf_start, "end": buf_end})

    return blocks


def _transcribe_with_qwen3_asr(
    audio_path: Path,
    language: Optional[str] = None,
) -> str:
    """Transcribe audio locally with Qwen3-ASR-1.7B. Returns SRT-formatted text."""
    from mlx_qwen3_asr import transcribe  # type: ignore

    print(f"  Running Qwen3-ASR-1.7B on: {audio_path.name}")
    result = transcribe(
        audio_path,
        model=QWEN3_ASR_MODEL,
        language=language,
        return_timestamps=True,
        verbose=False,
    )

    if not result.segments:
        return f"1\n00:00:00,000 --> 00:00:01,000\n{result.text.strip()}\n"

    subtitle_blocks = _group_words_into_subtitles(result.segments)

    srt_blocks: list[str] = []
    for i, block in enumerate(subtitle_blocks, 1):
        start = _seconds_to_srt_time(block["start"])
        end = _seconds_to_srt_time(block["end"])
        srt_blocks.append(f"{i}\n{start} --> {end}\n{block['text']}")

    return "\n\n".join(srt_blocks) + "\n"

# ─────────────────────────── Public API ─────────────────────────────────────

def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
    dry_run: bool = False,
) -> dict[Path, Path]:
    from srt_utils import parse_srt, clean_subtitle_text, write_srt  # type: ignore

    print(f"\n{'='*60}")
    print(f"ASR backend: Qwen3-ASR-1.7B (local MLX) {'[DRY RUN]' if dry_run else ''}")
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

            raw_srt = _transcribe_with_qwen3_asr(upload_path, language)

            if not raw_srt.strip():
                from usage_tracker import log_failure  # type: ignore
                log_failure("ASR", media_path.name, "Qwen3-ASR returned empty transcription")
                print(f"  [WARNING] Qwen3-ASR returned EMPTY transcription for {media_path.name}.")
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
                                "Qwen3-ASR may have returned garbled SRT format.")
                    print(f"  [WARNING] Only {len(entries)} entries for "
                          f"{duration_sec/60:.1f}min audio — ASR output may be garbled.")

            write_srt(entries, srt_path)
            txt_path = out_dir / f"{media_path.stem}.transcript.txt"
            txt_path.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")
            
            # Clean up extracted audio
            if upload_path != media_path and upload_path.exists():
                try: upload_path.unlink()
                except OSError: pass

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
    
    # 1. Transcribe locally with Qwen3-ASR-1.7B
    raw_srt = _transcribe_with_qwen3_asr(a_p, language)

    # 2. Clean and save result
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

