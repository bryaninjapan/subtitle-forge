import subprocess
import os
import hashlib
from pathlib import Path
from gemini_client import get_gemini_client
from google.genai import types

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
    except OSError: pass
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
    except OSError: return False

def check_audio_quality(media_path: Path) -> str:
    from config import OUTPUT_DIR
    client = get_gemini_client()
    tmp_audio = OUTPUT_DIR / f"quality_check_{os.getpid()}.wav"
    subprocess.run(["ffmpeg", "-i", str(media_path), "-t", "30", "-vn", "-ac", "1", "-ar", "16000", "-y", str(tmp_audio)], capture_output=True)
    if not tmp_audio.exists(): return "Unknown"
    try:
        up = client.files.upload(file=str(tmp_audio), config={"mime_type": "audio/wav"})
        from config import LITE_MODEL
        res = client.models.generate_content(
            model=LITE_MODEL,
            contents=[types.Part.from_uri(file_uri=up.uri, mime_type=up.mime_type)],
            config=types.GenerateContentConfig(system_instruction="Analyze audio quality. Is it clear? Return 'Good' or a short warning.")
        )
        client.files.delete(name=up.name); tmp_audio.unlink()
        return res.text.strip()
    except (OSError, KeyError):
        if tmp_audio.exists(): tmp_audio.unlink()
        return "Unknown"
