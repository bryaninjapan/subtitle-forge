#!/usr/bin/env python3
"""Subtitle Forge - Video subtitle generation and translation pipeline.

Usage:
    python main.py                          # Process all files in input/
    python main.py --input video.mp4        # Process a single file
    python main.py --input /path/to/folder  # Process all files in a folder
    python main.py --language Japanese      # Force source language
    python main.py --asr-only               # Only generate original subtitles
    python main.py --translate-only         # Only translate existing SRT files
    python main.py --notes-only             # Only generate study notes
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
    args: argparse.Namespace | None = None,
) -> None:
    """Run the full subtitle generation and translation pipeline.

    When multiple videos are provided and asr_only is not set, this uses an
    ASR->Translation pipeline where Video N's translation starts immediately
    after its ASR completes while Video N+1's ASR begins concurrently.
    """
    from concurrent.futures import ThreadPoolExecutor, Future, as_completed
    from asr_engine import transcribe_files
    from translator import translate_srt_files
    from notes_generator import generate_study_notes
    from vision_engine import extract_keyframes
    from config import ASR_MAX_CONCURRENT, OUTPUT_DIR

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

    # ── asr-only mode ─────────────────────────────────────────────────────────
    if asr_only:
        existing = find_existing_srts(media_files)
        to_transcribe = [f for f in media_files if f not in existing]
        if not to_transcribe:
            print("\nAll files already have original subtitles in output/. Nothing to do.")
            return
        if len(to_transcribe) < len(media_files):
            print(f"\n[--asr-only] Skipping {len(media_files) - len(to_transcribe)} file(s) that already have .srt")
        srt_mapping = transcribe_files(to_transcribe, language=language)
        _print_summary(start_time, len(srt_mapping))
        return

    # ── notes-only mode ────────────────────────────────────────────────────────
    if getattr(args, 'notes_only', False):
        print("\n[--notes-only] Generating study notes for all processed videos...")
        count = 0
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir():
                txt_path = d / f"{d.name}.txt"
                if txt_path.exists():
                    media_path = INPUT_DIR / f"{d.name}.mp4"
                    if not media_path.exists():
                        from config import VIDEO_EXTENSIONS
                        for ext in VIDEO_EXTENSIONS:
                            test_p = INPUT_DIR / f"{d.name}{ext}"
                            if test_p.exists():
                                media_path = test_p
                                break

                    if media_path.exists():
                        frames = []
                        if not getattr(args, 'no_vision', False):
                            try:
                                frames = extract_keyframes(media_path, d)
                            except Exception as e:
                                print(f"  [pipeline] Vision extraction failed for {d.name}: {e}")

                        generate_study_notes(media_path, txt_path.read_text(encoding="utf-8"), frame_paths=frames)
                        count += 1
                    else:
                        print(f"  [notes-only] [skip] Could not find media file for {d.name}")
        print(f"\nDone! Checked {count} video directory(s).")
        return

    # ── Single video: simple sequential flow ─────────────────────────────────
    if len(media_files) == 1:
        srt_mapping = transcribe_files(media_files, language=language)
        if srt_mapping:
            for media_path in srt_mapping:
                frames = []
                if not getattr(args, 'no_vision', False):
                    frames = extract_keyframes(media_path, OUTPUT_DIR / media_path.stem)
                txt_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}.txt"
                if txt_path.exists():
                    generate_study_notes(media_path, txt_path.read_text(encoding="utf-8"), frame_paths=frames)
            translate_srt_files(srt_mapping)
        _print_summary(start_time, len(srt_mapping) if srt_mapping else 0)
        return

    # ── Multi-video: overlap ASR(N+1) with Translation(N) ────────────────────
    print(f"\n⚡ Pipeline mode: {ASR_MAX_CONCURRENT}x ASR and 1x Translation across {len(media_files)} videos.\n")

    all_results_count = 0
    translation_futures: list[Future] = []

    translation_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="translator")
    asr_pool = ThreadPoolExecutor(max_workers=ASR_MAX_CONCURRENT, thread_name_prefix="asr")

    lock = __import__("threading").Lock()

    def process_video_task(v_path: Path):
        nonlocal all_results_count
        srt_mapping = transcribe_files([v_path], language=language)

        if srt_mapping:
            with lock:
                all_results_count += len(srt_mapping)

            for media_path in srt_mapping:
                frames = []
                if not getattr(args, 'no_vision', False):
                    try:
                        frames = extract_keyframes(media_path, OUTPUT_DIR / media_path.stem)
                    except Exception as e:
                        print(f"  [pipeline] Vision extraction failed for {media_path.name}: {e}")

                txt_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}.txt"
                if txt_path.exists():
                    try:
                        generate_study_notes(media_path, txt_path.read_text(encoding="utf-8"), frame_paths=frames)
                    except Exception as e:
                        print(f"  [pipeline] Study notes generation failed for {media_path.name}: {e}")

            future = translation_pool.submit(translate_srt_files, dict(srt_mapping))
            print(f"  [pipeline] ▶ ASR and Notes for '{v_path.name}' done. Translation queued.")
            return future
        else:
            print(f"  [pipeline] ✗ ASR failed for '{v_path.name}'.")
            return None

    try:
        asr_futures = [asr_pool.submit(process_video_task, vp) for vp in media_files]

        for f in as_completed(asr_futures):
            t_future = f.result()
            if t_future:
                translation_futures.append(t_future)

        if translation_futures:
            print(f"\n[pipeline] All ASR tasks complete. Finishing remaining translations...")
            for future in translation_futures:
                future.result()

    finally:
        asr_pool.shutdown(wait=False)
        translation_pool.shutdown(wait=False)

    _print_summary(start_time, all_results_count)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Subtitle Forge - Video subtitle generation and translation pipeline",
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
        "--notes-only",
        action="store_true",
        help="Generate study notes for all videos that have transcripts in output/",
    )
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Skip keyframe extraction to speed up note generation",
    )
    parser.add_argument(
        "--update-glossary",
        action="store_true",
        help="Scan all existing transcripts in output/ and update glossary.json",
    )
    args = parser.parse_args()

    if args.asr_only and args.translate_only:
        print("Error: Cannot use --asr-only and --translate-only together.")
        sys.exit(1)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.update_glossary:
        from glossary_manager import update_glossary_auto
        srts = sorted(OUTPUT_DIR.rglob("*.srt"))
        srts = [s for s in srts if not s.name.endswith(".zh.srt")]
        print(f"\n[--update-glossary] Scanning {len(srts)} transcript(s)...")
        for srt in srts:
            update_glossary_auto(srt)
        print("\nDone! glossary.json updated.")
        return

    run_pipeline(
        input_paths=args.input,
        language=args.language,
        asr_only=args.asr_only,
        translate_only=args.translate_only,
        args=args
    )


if __name__ == "__main__":
    main()
