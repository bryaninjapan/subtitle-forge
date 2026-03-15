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
import signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future, as_completed, wait

from config import INPUT_DIR, OUTPUT_DIR


def signal_handler(sig, frame):
    print("\n\n[SIGNAL] Interrupt received (Ctrl+C). Cleaning up before exiting...")
    # Attempt to clean up known WAV files in a best-effort way
    # We don't have access to all state here easily, but we can scan OUTPUT_DIR
    try:
        from config import OUTPUT_DIR
        for wav in OUTPUT_DIR.rglob("*.wav"):
            try:
                wav.unlink()
                print(f"  [cleanup] Removed: {wav.name}")
            except:
                pass
    except:
        pass
    print("Exiting.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


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
    from usage_tracker import get_total_usage
    from config import OUTPUT_DIR
    
    totals = get_total_usage()
    
    print(f"\n{'='*60}")
    print(f"Done! Processed {count} file(s) in {minutes}m {seconds}s")
    if totals:
        print(f"Total Token Usage: {totals.get('total', 0):,}")
        print(f"Estimated Total Cost: ${totals.get('cost', 0):.4f} USD")
    
    from config import load_glossary
    gloss = load_glossary()
    if gloss:
        print(f"Terminology Glossary: {len(gloss)} terms")
        
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
    from asr_engine import transcribe_files
    from translator import translate_srt_files
    from notes_generator import generate_study_notes
    from vision_engine import extract_keyframes
    from config import ASR_MAX_CONCURRENT, POST_PROC_MAX_CONCURRENT, OUTPUT_DIR

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

    def _cleanup_wav(media_path: Path):
        """Delete temporary WAV file if process is fully complete."""
        wav_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}.wav"
        if wav_path.exists():
            try:
                wav_path.unlink()
                print(f"  [cleanup] Removed temporary audio: {wav_path.name}")
            except Exception as e:
                print(f"  [cleanup] Failed to remove {wav_path.name}: {e}")

    # ── Single video: simple sequential flow ─────────────────────────────────
    if len(media_files) == 1:
        v_path = media_files[0]
        srt_path = OUTPUT_DIR / v_path.stem / f"{v_path.stem}.srt"
        zh_srt_path = OUTPUT_DIR / v_path.stem / f"{v_path.stem}.zh.srt"
        notes_path = OUTPUT_DIR / v_path.stem / f"{v_path.stem}_StudyNotes.md"
        
        # 1. ASR
        srt_mapping = {}
        if srt_path.exists():
            print(f"  [skip] ASR already done: {srt_path.name}")
            srt_mapping = {v_path: srt_path}
        else:
            srt_mapping = transcribe_files([v_path], language=language)
        
        # 2. Notes & Translation
        if srt_mapping:
            # Study Notes Checkpoint
            if notes_path.exists():
                print(f"  [skip] Study notes already exist: {notes_path.name}")
            else:
                frames = []
                if not getattr(args, 'no_vision', False):
                    frames = extract_keyframes(v_path, OUTPUT_DIR / v_path.stem)
                txt_path = OUTPUT_DIR / v_path.stem / f"{v_path.stem}.txt"
                if txt_path.exists():
                    generate_study_notes(v_path, txt_path.read_text(encoding="utf-8"), frame_paths=frames)
            
            # Translation Checkpoint
            if zh_srt_path.exists():
                print(f"  [skip] Translation already exists: {zh_srt_path.name}")
            else:
                translate_srt_files(srt_mapping)
                
            # Final Cleanup
            if zh_srt_path.exists():
                _cleanup_wav(v_path)
                
        _print_summary(start_time, len(srt_mapping) if srt_mapping else 0)
        return

    # ── Multi-video: overlap ASR(N+1) with Translation(N) ────────────────────
    print(f"\n⚡ Pipeline mode: {ASR_MAX_CONCURRENT}x ASR and {POST_PROC_MAX_CONCURRENT}x Post-processing across {len(media_files)} videos.\n")

    all_results_count = 0
    post_proc_futures: list[Future] = []
    video_start_times: dict[Path, float] = {}

    # Use a pool for post-processing (Notes + Translation)
    post_proc_pool = ThreadPoolExecutor(max_workers=POST_PROC_MAX_CONCURRENT, thread_name_prefix="post_proc")
    asr_pool = ThreadPoolExecutor(max_workers=ASR_MAX_CONCURRENT, thread_name_prefix="asr")

    lock = __import__("threading").Lock()

    def post_processing_task(media_path: Path, srt_path: Path):
        """Task that handles Notes generation and Translation sequentially for one video."""
        out_dir = OUTPUT_DIR / media_path.stem
        zh_srt_path = out_dir / f"{media_path.stem}.zh.srt"
        notes_path = out_dir / f"{media_path.stem}_StudyNotes.md"

        # 1. Study Notes
        if notes_path.exists():
            print(f"  [pipeline] [skip] Notes exist for '{media_path.name}'")
        else:
            frames = []
            if not getattr(args, 'no_vision', False):
                try:
                    frames = extract_keyframes(media_path, out_dir)
                except Exception as e:
                    print(f"  [pipeline] Vision extraction failed for {media_path.name}: {e}")

            txt_path = out_dir / f"{media_path.stem}.txt"
            if txt_path.exists():
                try:
                    generate_study_notes(media_path, txt_path.read_text(encoding="utf-8"), frame_paths=frames)
                except Exception as e:
                    print(f"  [pipeline] Study notes failed for {media_path.name}: {e}")

        # 2. Translation
        if zh_srt_path.exists():
            print(f"  [pipeline] [skip] Translation exists for '{media_path.name}'")
        else:
            try:
                # Wave 9: Style
                os.environ["TRANSLATION_STYLE"] = getattr(args, "style", "academic")
                translate_srt_files({media_path: srt_path})
            except Exception as e:
                print(f"  [pipeline] Translation failed for {media_path.name}: {e}")

        # 3. Chapters (Wave 9)
        if getattr(args, "chapters", False):
            try:
                from chapter_generator import generate_video_chapters
                txt_path = out_dir / f"{media_path.stem}.txt"
                if txt_path.exists():
                    generate_video_chapters(media_path, txt_path)
            except Exception as e:
                print(f"  [pipeline] Chapters failed for {media_path.name}: {e}")

    def process_video_task(v_path: Path):
        nonlocal all_results_count
        srt_path = OUTPUT_DIR / v_path.stem / f"{v_path.stem}.srt"
        
        # ASR Checkpoint
        if srt_path.exists():
            print(f"  [pipeline] [skip] ASR already done: {v_path.name}")
            srt_mapping = {v_path: srt_path}
        else:
            srt_mapping = transcribe_files([v_path], language=language)

        if srt_mapping:
            with lock:
                all_results_count += len(srt_mapping)

            # ETA calculation support
            video_end_time = time.time()
            v_duration = video_end_time - video_start_times.get(v_path, video_end_time)
            
            with lock:
                processed_count = all_results_count
                total_to_process = len(media_files)
                avg_time = (video_end_time - start_time) / processed_count
                remaining = total_to_process - processed_count
                eta_sec = avg_time * remaining
                eta_str = f"{int(eta_sec//60)}m {int(eta_sec%60)}s" if eta_sec > 0 else "N/A"
                print(f"  [pipeline] ASR for '{v_path.name}' done in {v_duration:.1f}s. (ETA Remaining: {eta_str})")

            # ASR is DONE. Now offload Notes + Translation to the post_proc_pool
            future = post_proc_pool.submit(post_processing_task, v_path, srt_path)
            return future
        else:
            print(f"  [pipeline] ✗ ASR failed for '{v_path.name}'.")
            return None

    try:
        asr_futures = []
        for i, vp in enumerate(media_files, 1):
            video_start_times[vp] = time.time()
            print(f"\n{'='*20} [{i}/{len(media_files)}] Processing: {vp.name} {'='*20}")
            asr_futures.append(asr_pool.submit(process_video_task, vp))

        for f in as_completed(asr_futures):
            pp_future = f.result()
            if pp_future:
                post_proc_futures.append(pp_future)

        if post_proc_futures:
            print(f"\n[pipeline] All ASR tasks complete. Finishing remaining post-processing...")
            for future in post_proc_futures:
                future.result()

        # Final pass cleanup for multi-video mode
        print("\n[pipeline] Performing final resource cleanup...")
        for vp in media_files:
            zh_srt_path = OUTPUT_DIR / vp.stem / f"{vp.stem}.zh.srt"
            if zh_srt_path.exists():
                _cleanup_wav(vp)

    finally:
        asr_pool.shutdown(wait=False)
        post_proc_pool.shutdown(wait=False)

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
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete all temporary .wav files in output directory and exit",
    )
    parser.add_argument(
        "--style",
        type=str,
        default="academic",
        choices=["academic", "casual", "exam-focused"],
        help="Translation style (Wave 9)",
    )
    parser.add_argument(
        "--chapters",
        action="store_true",
        help="Generate automatic video chapters based on transcript (Wave 9)",
    )
    args = parser.parse_args()

    if args.cleanup:
        print("\n[Cleanup] Cleaning up all temporary .wav files in output/...")
        count = 0
        for wav in OUTPUT_DIR.rglob("*.wav"):
            try:
                wav.unlink()
                count += 1
            except Exception as e:
                print(f"  Failed: {wav.name}: {e}")
        print(f"Done. Removed {count} file(s).")
        return

    if args.asr_only and args.translate_only:
        print("Error: Cannot use --asr-only and --translate-only together.")
        sys.exit(1)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-flight Check
    from asr_engine import check_dependencies
    check_dependencies()

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
