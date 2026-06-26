"""Media utilities — duration and file hash."""
import hashlib
import subprocess
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
    except OSError:
        pass
    return 0.0


def get_file_hash(path: Path) -> str:
    """Calculate SHA256 of the first 64KB for quick identification."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        chunk = f.read(65536)
        h.update(chunk)
    return h.hexdigest()
