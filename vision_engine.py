import subprocess
import os # Just in case
from pathlib import Path

def extract_keyframes(video_path: Path, output_dir: Path, interval_min: int = 5):
    """
    Extract frames from the video at regular intervals, with adaptive adjustment 
    to stay within MAX_FRAMES_PER_VIDEO.
    """
    from config import MAX_FRAMES_PER_VIDEO
    import math
    from media_utils import get_media_duration_sec

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Skip if frames already exist
    existing_frames = sorted(list(frames_dir.glob("*.jpg")))
    if existing_frames:
        print(f"  [Vision] [skip] Keyframes already exist in {frames_dir.name}")
        return existing_frames
    
    # Scene Change Detection Logic
    duration = get_media_duration_sec(video_path)
    print(f"  [Vision] Detecting scene changes for '{video_path.name}'...")
    
    # We use a combined approach: 
    # 1. Use ffmpeg scene detection to find unique frames
    # 2. Limit the number of frames to MAX_FRAMES_PER_VIDEO
    
    # Sensitivity 0.03 is usually good for slides. Lower is more sensitive.
    scene_threshold = 0.03
    
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{scene_threshold})',scale=1024:-1",
        "-vsync", "vfr",
        "-q:v", "2",
        str(frames_dir / "frame_%03d.jpg")
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        all_frames = sorted(list(frames_dir.glob("*.jpg")))
        
        # If too many frames, sample down to MAX_FRAMES_PER_VIDEO
        if len(all_frames) > MAX_FRAMES_PER_VIDEO:
            print(f"  [Vision] Detected {len(all_frames)} scenes. Downsampling to {MAX_FRAMES_PER_VIDEO}...")
            step = len(all_frames) / MAX_FRAMES_PER_VIDEO
            indices = [int(i * step) for i in range(MAX_FRAMES_PER_VIDEO)]
            to_keep = {all_frames[i] for i in indices}
            for f in all_frames:
                if f not in to_keep:
                    f.unlink()
            all_frames = sorted(list(frames_dir.glob("*.jpg")))
            
        print(f"  [Vision] Captured {len(all_frames)} unique visual scenes.")
        return all_frames
    except subprocess.CalledProcessError as e:
        print(f"  [Vision] Scene detection failed: {e.stderr.decode()}. Falling back to interval sampling...")
        # Fallback to simple interval if duration is known
        interval_min = 5
        if duration > 0:
            interval_min = max(1, math.ceil(duration / (MAX_FRAMES_PER_VIDEO * 60)))
        
        fallback_cmd = [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps=1/({interval_min}*60),scale=1024:-1",
            "-q:v", "2",
            str(frames_dir / "frame_%03d.jpg")
        ]
        subprocess.run(fallback_cmd, capture_output=True)
        return sorted(list(frames_dir.glob("*.jpg")))
    except Exception as e:
        print(f"  [Vision] Frame extraction failed: {e}")
        return []


# media_utils.get_media_duration_sec is imported at the top of extract_keyframes

