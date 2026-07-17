"""Hard-burn subtitles into video using ffmpeg.

Supports single-file and batch burning with bilingual subtitle auto-detection.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def burn_subtitles(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    font_size: int = 24,
) -> bool:
    """Hard-burn a single subtitle file into a video using ffmpeg.

    Args:
        video_path: Source video file.
        subtitle_path: SRT subtitle file (monolingual or bilingual).
        output_path: Output video file with burned-in subtitles.
        font_size: Font size for subtitles (default: 24).

    Returns:
        True if successful, False on error.
    """
    sub_arg = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
    vf = f"subtitles='{sub_arg}':fontsize={font_size}"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", vf,
        "-c:a", "copy", "-y", str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=3600)
        return True
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return False


def find_best_subtitle(video_name: str, search_dirs: list[Path]) -> Optional[Path]:
    """Find the best matching subtitle for a video.

    Priority: bilingual.srt > .srt > .zh.srt
    Checks in each search_dir in order.
    """
    stem = Path(video_name).stem
    patterns = [
        f"{stem}.bilingual.srt",
        f"{stem}.srt",
        f"{stem}.zh.srt",
    ]
    for d in search_dirs:
        for pattern in patterns:
            p = d / pattern
            if p.exists():
                return p
    return None


def batch_burn(
    video_paths: list[Path],
    subtitle_search_dirs: list[Path],
    output_dir: Path,
    font_size: int = 24,
    suffix: str = "_burned",
) -> list[Path]:
    """Batch burn subtitles for multiple videos.

    For each video, finds the best matching subtitle in search_dirs,
    burns it in, and saves to output_dir with the given suffix.

    Args:
        video_paths: List of source video files.
        subtitle_search_dirs: Directories to search for subtitle files.
        output_dir: Output directory for burned videos.
        font_size: Font size for subtitles.
        suffix: Suffix to add before extension (e.g. "_burned").

    Returns:
        List of successfully created output video paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []

    for i, video_path in enumerate(video_paths, 1):
        print(f"  [{i}/{len(video_paths)}] Burning: {video_path.name}")

        sub_path = find_best_subtitle(video_path.name, subtitle_search_dirs)
        if not sub_path:
            print(f"    [skip] No subtitle found for {video_path.name}")
            continue

        out_name = f"{video_path.stem}{suffix}{video_path.suffix}"
        out_path = output_dir / out_name

        ok = burn_subtitles(video_path, sub_path, out_path, font_size=font_size)
        if ok:
            print(f"    ✅ Saved: {out_path.name}")
            results.append(out_path)
        else:
            print(f"    [ERROR] Failed to burn: {video_path.name}")

    return results
