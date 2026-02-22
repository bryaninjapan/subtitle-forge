#!/usr/bin/env python3
"""Subtitle Forge - Local video subtitle generation and translation pipeline.

Usage:
    python main.py                          # Process all files in input/
    python main.py --input video.mp4        # Process a single file
    python main.py --input /path/to/folder  # Process all files in a folder
    python main.py --language Japanese       # Force source language
    python main.py --asr-only               # Only generate original subtitles
    python main.py --translate-only         # Only translate existing SRT files
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from config import INPUT_DIR, OUTPUT_DIR


def find_media_files(input_path: Path) -> list[Path]:
    """Find all supported media files in the given path."""
    from asr_engine import is_media_file

    if input_path.is_file():
        if is_media_file(input_path):
            return [input_path]
        else:
            print(f"Error: Unsupported file format: {input_path.suffix}")
            return []

    if input_path.is_dir():
        files = sorted(
            f for f in input_path.iterdir()
            if f.is_file() and is_media_file(f)
        )
        return files

    print(f"Error: Path not found: {input_path}")
    return []


def find_existing_srts(media_files: list[Path]) -> dict[Path, Path]:
    """Find existing original-language SRT files for given media files."""
    mapping: dict[Path, Path] = {}
    for media_path in media_files:
        srt_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}.srt"
        if srt_path.exists():
            mapping[media_path] = srt_path
    return mapping


def run_pipeline(
    input_path: Path,
    language: str | None = None,
    asr_only: bool = False,
    translate_only: bool = False,
) -> None:
    """Run the full subtitle generation and translation pipeline."""
    from asr_engine import transcribe_files
    from translator import translate_srt_files

    start_time = time.time()

    media_files = find_media_files(input_path)
    if not media_files:
        print("No supported media files found.")
        return

    print(f"\nFound {len(media_files)} file(s):")
    for f in media_files:
        print(f"  - {f.name}")

    # Phase 1: ASR
    if translate_only:
        print("\n[--translate-only] Skipping ASR, looking for existing SRT files...")
        srt_mapping = find_existing_srts(media_files)
        if not srt_mapping:
            print("No existing SRT files found in output/. Run ASR first.")
            return
        print(f"Found {len(srt_mapping)} existing SRT file(s).")
    else:
        srt_mapping = transcribe_files(media_files, language=language)

    if not srt_mapping:
        print("\nNo files were transcribed successfully.")
        return

    # Phase 2: Translation
    if asr_only:
        print("\n[--asr-only] Skipping translation.")
    else:
        translate_srt_files(srt_mapping)

    # Summary
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"\n{'='*60}")
    print(f"Done! Processed {len(srt_mapping)} file(s) in {minutes}m {seconds}s")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Subtitle Forge - Local video subtitle generation and translation",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=INPUT_DIR,
        help=f"Input file or directory (default: {INPUT_DIR})",
    )
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=None,
        help="Force source language (e.g., English, Japanese). Default: auto-detect",
    )
    parser.add_argument(
        "--asr-only",
        action="store_true",
        help="Only run ASR, skip translation",
    )
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Only translate existing SRT files, skip ASR",
    )
    args = parser.parse_args()

    if args.asr_only and args.translate_only:
        print("Error: Cannot use --asr-only and --translate-only together.")
        sys.exit(1)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_pipeline(
        input_path=args.input,
        language=args.language,
        asr_only=args.asr_only,
        translate_only=args.translate_only,
    )


if __name__ == "__main__":
    main()
