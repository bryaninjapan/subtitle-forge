"""ASR engine wrapping mlx-qwen3-asr for batch video transcription."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from config import (
    AUDIO_SAMPLE_RATE,
    ASR_MODEL,
    FFMPEG_BIN,
    OUTPUT_DIR,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
)


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract audio from a video file to 16kHz mono WAV using ffmpeg."""
    audio_path = output_dir / f"{video_path.stem}.wav"
    if audio_path.exists():
        print(f"  [skip] Audio already extracted: {audio_path.name}")
        return audio_path

    cmd = [
        FFMPEG_BIN, "-i", str(video_path),
        "-vn",                      # no video
        "-acodec", "pcm_s16le",     # 16-bit PCM
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "1",                 # mono
        "-y",                       # overwrite
        str(audio_path),
    ]
    print(f"  Extracting audio: {video_path.name} -> {audio_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    return audio_path


def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def transcribe_files(
    media_files: list[Path],
    language: str | None = None,
) -> dict[Path, Path]:
    """Transcribe a list of media files and write original-language SRT files.

    Returns a mapping of {media_path: srt_path} for successfully transcribed files.
    """
    from mlx_qwen3_asr import Session
    from mlx_qwen3_asr.writers import write_srt

    print(f"\n{'='*60}")
    print(f"Loading ASR model: {ASR_MODEL}")
    print(f"{'='*60}")
    t0 = time.time()
    session = Session(model=ASR_MODEL)
    print(f"Model loaded in {time.time() - t0:.1f}s\n")

    results: dict[Path, Path] = {}

    for i, media_path in enumerate(media_files, 1):
        print(f"[{i}/{len(media_files)}] Processing: {media_path.name}")
        out_dir = OUTPUT_DIR / media_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            if media_path.suffix.lower() in AUDIO_EXTENSIONS:
                audio_path = media_path
            else:
                audio_path = extract_audio(media_path, out_dir)

            srt_path = out_dir / f"{media_path.stem}.srt"

            print(f"  Transcribing ({language or 'auto-detect'})...")
            t1 = time.time()
            result = session.transcribe(
                str(audio_path),
                language=language,
                return_timestamps=True,
                verbose=False,
            )
            elapsed = time.time() - t1
            print(f"  Language: {result.language}")
            print(f"  Transcription done in {elapsed:.1f}s")

            write_srt(result, str(srt_path))
            print(f"  Saved: {srt_path.name}")

            results[media_path] = srt_path

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")

    return results
