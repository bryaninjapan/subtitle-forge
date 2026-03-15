import subprocess
from pathlib import Path

def extract_keyframes(video_path: Path, output_dir: Path, interval_min: int = 5):
    """
    Extract frames from the video at regular intervals.
    Saved to output_dir/frames/
    """
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract one frame every X minutes
    # Using fps filter to pick 1 frame every (interval_min * 60) seconds
    fps = 1 / (interval_min * 60)
    
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2", # High quality
        str(frames_dir / "frame_%03d.jpg")
    ]
    
    print(f"  [Vision] Extracting keyframes every {interval_min} minutes...")
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        # Return list of extracted frame paths
        return sorted(list(frames_dir.glob("*.jpg")))
    except subprocess.CalledProcessError as e:
        print(f"  [Vision] Frame extraction failed: {e.stderr.decode()}")
        return []

