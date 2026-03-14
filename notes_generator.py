import os
from pathlib import Path
from google import genai
from google.genai import types

def generate_study_notes(media_path: Path, transcript_text: str):
    """Generate professional CFA study notes from the transcript using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return
        
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    print(f"  [Study Notes] Generating notes for '{media_path.name}'...")
    
    from config import OUTPUT_DIR
    notes_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}_StudyNotes.md"
    if notes_path.exists():
        print(f"  [Study Notes] [skip] Notes already exist: {notes_path.name}")
        return

    prompt = f"""
You are an expert CFA (Chartered Financial Analyst) tutor. I will provide a transcript of a CFA Level 1 lecture.
Your task is to create comprehensive, well-structured study notes in Traditional Chinese (Taiwan).

Please include the following sections:
1. **課程摘要 (Summary)**: A high-level overview of the video's content.
2. **核心概念 (Key Concepts)**: Detailed explanations of professional terms and theories mentioned.
3. **重要公式 (Important Formulas)**: List any formulas mentioned with variable definitions.
4. **考試重點 (Exam Focus)**: Specific tips or areas that are likely to appear on the CFA exam.
5. **中英術語對照 (Terminology Table)**: A table of technical terms used in the video.

Transcript:
{transcript_text}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2, # Slightly more creative/structured than 0.0
            )
        )
        
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        
        notes_content = f"# CFA Study Notes: {media_path.stem}\n\n" + response.text
        notes_path.write_text(notes_content, encoding="utf-8")
        print(f"  [Study Notes] Saved: {notes_path.name}")
        
    except Exception as e:
        print(f"  [Study Notes] Failed to generate: {e}")
