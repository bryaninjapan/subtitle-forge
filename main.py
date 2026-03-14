#!/usr/bin/env python3
"""Subtitle Forge - Local video subtitle generation and translation pipeline.

Usage:
    python main.py                          # Process all files in input/
    python main.py --input video.mp4        # Process a single file
    python main.py --input /path/to/folder  # Process all files in a folder
    python main.py --language Japanese       # Force source language
    python main.py --asr-only               # Only generate original subtitles
    python main.py --translate-only         # Only translate existing SRT files
    python main.py --transcript-only        # Only output plain-text transcript (no SRT, no translation)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from config import INPUT_DIR, OUTPUT_DIR


def find_media_files(input_paths: list[Path]) -> list[Path]:
    """Find all supported media files in the given list of paths."""
    from asr_engine import is_media_file

    all_files: list[Path] = []
    
    for input_path in input_paths:
        if input_path.is_file():
            if is_media_file(input_path):
                all_files.append(input_path)
            else:
                print(f"Warning: Unsupported file format: {input_path.suffix} for {input_path.name}")
        elif input_path.is_dir():
            files = sorted(
                f for f in input_path.iterdir()
                if f.is_file() and is_media_file(f)
            )
            all_files.extend(files)
        else:
            print(f"Warning: Path not found: {input_path}")
    
    # Remove duplicates while preserving order
    unique_files: list[Path] = []
    seen = set()
    for f in all_files:
        if f not in seen:
            unique_files.append(f)
            seen.add(f)
            
    return unique_files


def find_existing_srts(media_files: list[Path]) -> dict[Path, Path]:
    """Find existing original-language SRT files for given media files."""
    mapping: dict[Path, Path] = {}
    for media_path in media_files:
        srt_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}.srt"
        if srt_path.exists():
            mapping[media_path] = srt_path
    return mapping


def _print_summary(start_time: float, count: int) -> None:
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    from config import OUTPUT_DIR
    print(f"\n{'='*60}")
    print(f"Done! Processed {count} file(s) in {minutes}m {seconds}s")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}")


def run_pipeline(
    input_paths: list[Path],
    language: str | None = None,
    asr_only: bool = False,
    translate_only: bool = False,
    transcript_only: bool = False,
) -> None:
    """Run the full subtitle generation and translation pipeline.

    When multiple videos are provided and neither asr_only nor transcript_only
    is set, this uses an ASR->Translation pipeline:
      - Video N's translation starts immediately in a background thread after
        its ASR completes.
      - Video N+1's ASR begins while Video N is still being translated.
    This overlapping reduces total wall-clock time significantly.
    """
    from concurrent.futures import ThreadPoolExecutor, Future
    from asr_engine import transcribe_files
    from translator import translate_srt_files

    start_time = time.time()

    media_files = find_media_files(input_paths)
    if not media_files:
        print("No supported media files found.")
        return

    print(f"\nFound {len(media_files)} file(s):")
    for f in media_files:
        print(f"  - {f.name}")

    # ── translate-only mode ────────────────────────────────────────────────────
    if translate_only:
        print("\n[--translate-only] Skipping ASR, looking for existing SRT files...")
        srt_mapping = find_existing_srts(media_files)
        if not srt_mapping:
            print("No existing SRT files found in output/. Run ASR first.")
            return
        print(f"Found {len(srt_mapping)} existing SRT file(s).")
        translate_srt_files(srt_mapping)
        _print_summary(start_time, len(srt_mapping))
        return

    # ── determine which files need ASR ────────────────────────────────────────
    to_transcribe = media_files
    if asr_only:
        existing = find_existing_srts(media_files)
        to_transcribe = [f for f in media_files if f not in existing]
        if not to_transcribe:
            print("\nAll files already have original subtitles in output/. Nothing to do.")
            return
        if len(to_transcribe) < len(media_files):
            print(f"\n[--asr-only] Skipping {len(media_files) - len(to_transcribe)} file(s) that already have .srt")
        srt_mapping = transcribe_files(to_transcribe, language=language, transcript_only=transcript_only)
        _print_summary(start_time, len(srt_mapping))
        return

    if transcript_only:
        srt_mapping = transcribe_files(to_transcribe, language=language, transcript_only=True)
        _print_summary(start_time, len(srt_mapping))
        return

    # ── Full pipeline: overlap ASR(N+1) with Translation(N) ──────────────────
    if len(to_transcribe) == 1:
        # Single video: pipeline has no benefit, keep it simple
        srt_mapping = transcribe_files(to_transcribe, language=language)
        if srt_mapping:
            translate_srt_files(srt_mapping)
        _print_summary(start_time, len(srt_mapping) if srt_mapping else 0)
        return

    print(f"\n⚡ Pipeline mode: ASR and Translation will overlap across {len(to_transcribe)} videos.\n")

    all_results_count = 0
    translation_futures: list[Future] = []

    # Single background thread for translation keeps things orderly and avoids
    # flooding the API with too many concurrent upload + translation requests.
    translation_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translator")

    try:
        for video_path in to_transcribe:
            # ASR blocks here — either GPU or cloud upload/inference
            srt_mapping = transcribe_files([video_path], language=language)

            if srt_mapping:
                all_results_count += len(srt_mapping)
                # Kick off translation immediately in background
                future = translation_pool.submit(translate_srt_files, dict(srt_mapping))
                translation_futures.append(future)
                print(f"  [pipeline] ▶ Translation for '{video_path.name}' running in background.")
            else:
                print(f"  [pipeline] ✗ ASR failed for '{video_path.name}', skipping translation.")

        # All ASR done — wait for remaining translations
        if translation_futures:
            print(f"\n[pipeline] All ASR complete. Waiting for {len(translation_futures)} translation task(s)...")
            for future in translation_futures:
                future.result()  # Re-raises any exception from the background thread

    finally:
        translation_pool.shutdown(wait=False)

    _print_summary(start_time, all_results_count)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Subtitle Forge - Local video subtitle generation and translation",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        nargs="+",
        default=[INPUT_DIR],
        help=f"Input file(s) or directory/directories (default: [{INPUT_DIR}])",
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
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Only output plain-text transcript (no SRT, no translation)",
    )
    args = parser.parse_args()

    if args.asr_only and args.translate_only:
        print("Error: Cannot use --asr-only and --translate-only together.")
        sys.exit(1)
    if args.transcript_only and args.translate_only:
        print("Error: Cannot use --transcript-only and --translate-only together.")
        sys.exit(1)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_pipeline(
        input_paths=args.input,
        language=args.language,
        asr_only=args.asr_only,
        translate_only=args.translate_only,
        transcript_only=args.transcript_only,
    )


if __name__ == "__main__":
    main()
