import os
from pathlib import Path
from google import genai
from google.genai import types
from usage_tracker import log_usage

def generate_study_notes(media_path: Path, transcript_text: str, frame_paths: list[Path] | None = None):
    """Generate professional CFA study notes from the transcript using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("  [Study Notes] ERROR: GEMINI_API_KEY not found. Skipping note generation.")
        return
        
    from config import DEFAULT_GEMINI_MODEL, OUTPUT_DIR
    
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    print(f"  [Study Notes] Generating notes for '{media_path.name}'...")
    
    notes_path = OUTPUT_DIR / media_path.stem / f"{media_path.stem}_StudyNotes.md"
    if notes_path.exists():
        print(f"  [Study Notes] [skip] Notes already exist: {notes_path.name}")
        return

    # Truncate transcript to avoid exceeding Gemini's 1M token limit
    # ~150K chars ≈ 37K tokens, leaves plenty of headroom for prompt + output
    MAX_TRANSCRIPT_CHARS = 150_000
    truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        truncated += "\n\n[transcript truncated for length]"

    prompt = f"""
You are an expert CFA (Chartered Financial Analyst) tutor. Below is a transcript of a CFA Level 1 lecture, along with several keyframes from the video.
Your task is to create comprehensive, well-structured study notes in Traditional Chinese (Taiwan).

Please integrate information from the images (slides, charts) with the transcript text to provide a complete picture.

Sections to include:
1. **課程摘要 (Summary)**: A high-level overview of the video's content.
2. **核心概念 (Key Concepts)**: Detailed explanations of professional terms and theories mentioned. Reference the slides if they contain definitions or charts.
3. **重要公式 (Important Formulas)**: List any formulas mentioned with variable definitions.
4. **考試重點 (Exam Focus)**: Specific tips or areas that are likely to appear on the CFA exam.
5. **中英術語對照 (Terminology Table)**: A table of technical terms used in the video.

### Transcript:
{truncated}
"""

    contents = [prompt]
    
    if frame_paths:
        frame_links = "\n\n### 課程投影片回顧\n"
        for i, fp in enumerate(frame_paths, 1):
            # 1. Add to prompt's bottom links (original behavior preserved)
            rel_path = f"frames/{fp.name}"
            frame_links += f"![投影片 {i}]({rel_path})\n"
            
            # 2. Add as Multimodal parts for AI to "see"
            try:
                contents.append(types.Part.from_bytes(
                    data=fp.read_bytes(),
                    mime_type="image/jpeg"
                ))
            except Exception as e:
                print(f"  [Study Notes] Failed to attach image {fp.name}: {e}")
    else:
        frame_links = ""

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2, # Slightly more creative/structured than 0.0
            )
        )
    except Exception as e:
        print(f"  [Study Notes] Multimodal generation failed: {e}. Retrying with text-only mode...")
        try:
            # Fallback to text-only mode
            response = client.models.generate_content(
                model=model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0, # More deterministic for fallback
                )
            )
        except Exception as e2:
            print(f"  [Study Notes] Critical Failure: Text-only fallback also failed: {e2}")
            return

    try:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        
        notes_content = f"# CFA Study Notes: {media_path.stem}\n\n" + response.text
        if frame_paths and "Multimodal generation failed" not in str(locals().get('e', '')):
             notes_content += frame_links
             
        notes_path.write_text(notes_content, encoding="utf-8")
        print(f"  [Study Notes] Saved: {notes_path.name}")
        
        # Log usage
        if response.usage_metadata:
            log_usage(
                "Notes",
                media_path.name,
                response.usage_metadata.prompt_token_count,
                response.usage_metadata.candidates_token_count,
            )
            print(f"  Token Usage (Notes): Input={response.usage_metadata.prompt_token_count}, Output={response.usage_metadata.candidates_token_count}, Total={response.usage_metadata.total_token_count}")
        
    except Exception as e:
        print(f"  [Study Notes] Failed to write file: {e}")
