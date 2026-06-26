"""Hard-burn subtitles into video using ffmpeg."""
import subprocess
from pathlib import Path


def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path):
    """Hard-burn subtitles into video using ffmpeg."""
    sub_arg = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"subtitles='{sub_arg}'",
        "-c:a", "copy", "-y", str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except OSError:
        return False
