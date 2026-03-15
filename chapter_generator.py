import os
import re
from pathlib import Path
from google import genai
from google.genai import types
from srt_utils import parse_srt

def generate_video_chapters(media_path: Path, transcript_path: Path):
    """Analyze transcript to identify topic shifts (LOS) and generate chapters."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return
        
    from config import DEFAULT_GEMINI_MODEL, OUTPUT_DIR
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    print(f"  [Chapters] Identifying logical chapters for '{media_path.name}'...")
    
    try:
        transcript = transcript_path.read_text(encoding="utf-8")
        # Truncate if too long (standard 150k chars)
        truncated = transcript[:150000]
        
        system_instruction = """
You are a CFA academic editor. Analyze the provided transcript to identify logical topic shifts, specifically focusing on CFA Learning Outcome Statements (LOS A, LOS B, etc.) and major technical concepts.

Generate a YouTube-style timestamp list (HH:MM:SS Title).
Example:
00:00:00 Introduction & Overview
00:05:30 [LOS A] Ethics and Trust
00:15:20 [LOS B] Code of Ethics
00:45:10 Conclusion & EOCQ

Rules:
- 100% strictly Traditional Chinese (Taiwan).
- At least 3 chapters, maximum 10.
- Output ONLY the list of chapters.
"""
        
        response = client.models.generate_content(
            model=model,
            contents=[f"### Transcript ###\n{truncated}"],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
        )
        
        chapters_text = response.text.strip()
        chapters_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}_Chapters.txt"
        chapters_path.write_text(chapters_text, encoding="utf-8")
        print(f"  [Chapters] Saved: {chapters_path.name}")
        return chapters_path
        
    except Exception as e:
        print(f"  [Chapters] Failed to generate chapters: {e}")
        return None
