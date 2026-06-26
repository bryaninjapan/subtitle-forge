import os
import subprocess
from pathlib import Path
from google.genai import types  # type: ignore
from usage_tracker import log_usage  # type: ignore
from gemini_client import get_gemini_client  # type: ignore
from openrouter_client import get_openrouter_client  # type: ignore
from config import OPENROUTER_TEXT_MODEL  # type: ignore

def _get_gemini_client():
    return get_gemini_client()

def _compress_image(fp: Path) -> bytes:
    """Resize image to max 1024px using ffmpeg to save tokens."""
    compressed_fp = fp.with_suffix(".tmp.jpg")
    try:
        # Resize to max 1024px width/height while maintaining aspect ratio
        subprocess.run([
            "ffmpeg", "-y", "-i", str(fp),
            "-vf", "scale='if(gt(iw,ih),min(1024,iw),-1)':'if(gt(ih,iw),min(1024,ih),-1)'",
            "-q:v", "5", str(compressed_fp)
        ], capture_output=True, check=True)
        data = compressed_fp.read_bytes()
        compressed_fp.unlink()
        return data
    except Exception as e:
        print(f"  [Study Notes] Warning: Compression failed for {fp.name}: {e}")
        return fp.read_bytes()

def generate_study_notes(working_dir: Path, transcript_text: str, frame_paths: list[Path] | None = None):
    """Generate professional CFA study notes from the transcript using Gemini."""
    client = _get_gemini_client()
    if not client:
        print("  [Study Notes] ERROR: Gemini client not available. Skipping.")
        return
        
    from config import DEFAULT_GEMINI_MODEL  # type: ignore
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    v_name = working_dir.name
    print(f"  [Study Notes] Generating notes for '{v_name}'...")
    
    notes_path = working_dir / f"{v_name}.studynotes.md"
    if notes_path.exists():
        print(f"  [Study Notes] [skip] Notes already exist: {notes_path.name}")
        return notes_path.read_text(encoding="utf-8")

    MAX_TRANSCRIPT_CHARS = 100_000
    truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]  # type: ignore
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        truncated += "\n\n[transcript truncated for length]"

    from config import STUDY_NOTES_PROMPT
    system_instruction = STUDY_NOTES_PROMPT

    prompt = f"### Transcript:\n{truncated}"
    contents = [prompt]
    
    frame_links = ""
    if frame_paths:
        print(f"  [Study Notes] Processing {len(frame_paths)} keyframes with compression...")
        frame_links = "\n\n### 課程投影片回顧\n"
        for i, fp in enumerate(frame_paths, 1):
            if not fp.exists(): continue
            
            # 1. Add to markdown links
            rel_path = f"frames/{fp.name}"
            frame_links += f"![投影片 {i}]({rel_path})\n"
            
            # 2. Add as Multimodal part (compressed)
            try:
                img_bytes = _compress_image(fp)
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            except Exception as e:
                print(f"  [Study Notes] Failed to attach {fp.name}: {e}")

    try:
        from usage_tracker import check_backoff  # type: ignore
        check_backoff()
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )
        
        usage = response.usage_metadata
        if usage:
            log_usage("Notes", v_name, usage.prompt_token_count, usage.candidates_token_count)
            print(f"  Token Usage (Notes): Input={usage.prompt_token_count}, Output={usage.candidates_token_count}")

    except Exception as e:
        print(f"  [Study Notes] Multimodal failed: {e}. Trying text-only fallback (OpenRouter)...")
        try:
            or_client = get_openrouter_client()
            or_model = os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL)
            or_res = or_client.chat.completions.create(
                model=or_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            # Wrap in a simple namespace so response.text works below
            class _Resp:
                text = (or_res.choices[0].message.content or "").strip()
                usage_metadata = None
            response = _Resp()
            fallback_in = or_res.usage.prompt_tokens if or_res.usage else 0
            fallback_out = or_res.usage.completion_tokens if or_res.usage else 0
            log_usage("Notes", v_name, fallback_in, fallback_out, model=or_model)
        except Exception as e2:
            print(f"  [Study Notes] Critical Failure: {e2}")
            from usage_tracker import log_failure  # type: ignore
            log_failure("Notes", v_name, str(e2))
            raise e2

    try:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_content = f"# CFA Study Notes: {v_name}\n\n" + response.text
        if frame_links:
            notes_content += frame_links
             
        notes_path.write_text(notes_content, encoding="utf-8")
        print(f"  [Study Notes] Saved: {notes_path.name}")
        return notes_content
    except Exception as e:
        from usage_tracker import log_failure  # type: ignore
        log_failure("Notes", v_name, f"Error writing file: {e}")
        print(f"  [Study Notes] Error writing file: {e}")
        raise e
