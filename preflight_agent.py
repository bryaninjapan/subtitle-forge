#!/usr/bin/env python3
"""
preflight_agent.py — Prep work for the Subtitle Forge pipeline.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any

from media_utils import check_audio_quality # type: ignore

def extract_audio_and_validate(video_path: str, working_directory: str) -> Dict[str, Any]:
    """Extract audio in standard 16khz mono WAV format for Gemini Flex/Flash."""
    v_p = Path(video_path)
    w_d = Path(working_directory)
    audio_path = w_d / f"{v_p.stem}_16k.wav"
    
    # 1. Extraction (ffmpeg)
    if not audio_path.exists():
        subprocess.run([
            "ffmpeg", "-i", str(v_p),
            "-vn", "-ac", "1", "-ar", "16000",
            "-y", str(audio_path)
        ], capture_output=True, check=True)
        
    # 2. Quality check
    quality = check_audio_quality(v_p)
    
    return {
        "audio_16khz_path": str(audio_path),
        "audio_quality_report": quality
    }
