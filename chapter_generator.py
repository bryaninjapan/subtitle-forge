import os
from pathlib import Path
from openrouter_client import get_openrouter_client  # type: ignore
from config import OPENROUTER_TEXT_MODEL  # type: ignore

def generate_video_chapters(working_dir: Path, video_name: str, transcript_text: str):
    """Analyze transcript to identify topic shifts (LOS) and generate chapters."""
    client = get_openrouter_client()
    model = os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL)

    print(f"  [Chapters] Identifying logical chapters for '{video_name}'...")

    try:
        truncated = transcript_text[0:120000]  # type: ignore[misc]

        system_instruction = """
You are a CFA academic editor. Analyze the provided transcript to identify logical topic shifts, specifically focusing on CFA Learning Outcome Statements (LOS A, LOS B, etc.) and major technical concepts.

Generate a YouTube-style timestamp list (HH:MM:SS Title).
Example:
00:00:00 Introduction & Overview
00:05:30 [LOS A] Ethics and Trust
00:15:20 [LOS B] Code of Ethics
00:45:10 Conclusion & EOCQ

Rules:
- 100% strictly Simplified Chinese.
- At least 3 chapters, maximum 10.
- Output ONLY the list of chapters.
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"### Transcript ###\n{truncated}"},
            ],
            temperature=0.0,
        )

        chapters_text = (response.choices[0].message.content or "").strip()
        stem = Path(video_name).stem
        chapters_path = working_dir / f"{stem}.chapter.txt"
        chapters_path.write_text(chapters_text, encoding="utf-8")
        print(f"  [Chapters] Saved: {chapters_path.name}")
        return chapters_text

    except Exception as e:
        print(f"  [Chapters] Failed to generate chapters: {e}")
        raise e
