import subprocess
import os
import hashlib
import re
from pathlib import Path

def get_media_duration_sec(path: Path) -> float:
    """Return duration in seconds via ffprobe; 0.0 if unavailable."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())
    except: pass
    return 0.0

def get_file_hash(path: Path) -> str:
    """Calculate SHA256 of the first 64KB for quick identification."""
    if not path.exists(): return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        chunk = f.read(65536)
        h.update(chunk)
    return h.hexdigest()

def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path):
    """Hard-burn subtitles into video using ffmpeg."""
    # Escape path for ffmpeg filter: replace \ with \\ and : with \:
    sub_arg = str(subtitle_path).replace("\\", "\\\\").replace(":", "\\:")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"subtitles='{sub_arg}'",
        "-c:a", "copy", "-y", str(output_path)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except: return False

def check_audio_quality(media_path: Path) -> str:
    """Check audio quality using ffmpeg volumedetect (no API call needed)."""
    from config import OUTPUT_DIR
    tmp_audio = OUTPUT_DIR / f"quality_check_{os.getpid()}.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-i", str(media_path), "-t", "30", "-vn", "-ac", "1", "-ar", "16000", "-y", str(tmp_audio)],
            capture_output=True,
        )
        if not tmp_audio.exists():
            return "Unknown"
        result = subprocess.run(
            ["ffmpeg", "-i", str(tmp_audio), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True,
        )
        mean_match = re.search(r"mean_volume: ([-\d.]+) dB", result.stderr)
        max_match = re.search(r"max_volume: ([-\d.]+) dB", result.stderr)
        if mean_match and max_match:
            mean_db = float(mean_match.group(1))
            max_db = float(max_match.group(1))
            if max_db < -30:
                return "Warning: Very low audio level"
            if mean_db < -40:
                return "Warning: Low average volume"
            return "Good"
        return "Unknown"
    except:
        return "Unknown"
    finally:
        if tmp_audio.exists():
            try: tmp_audio.unlink()
            except: pass
