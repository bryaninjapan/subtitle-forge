import os
import base64
import subprocess
from pathlib import Path
from usage_tracker import log_usage  # type: ignore
from openrouter_client import get_openrouter_client  # type: ignore
from config import OPENROUTER_TEXT_MODEL  # type: ignore

def _compress_image(fp: Path) -> bytes:
    """Resize image to max 1024px using ffmpeg to save tokens."""
    compressed_fp = fp.with_suffix(".tmp.jpg")
    try:
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
    """Generate professional CFA study notes from the transcript using OpenRouter."""
    client = get_openrouter_client()
    model = os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL)

    v_name = working_dir.name
    print(f"  [Study Notes] Generating notes for '{v_name}'...")

    notes_path = working_dir / f"{v_name}.studynotes.md"
    if notes_path.exists():
        print(f"  [Study Notes] [skip] Notes already exist: {notes_path.name}")
        return notes_path.read_text(encoding="utf-8")

    MAX_TRANSCRIPT_CHARS = 100_000
    truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        truncated += "\n\n[transcript truncated for length]"

    system_instruction = """
You are an expert CFA (Chartered Financial Analyst) tutor.
Your task is to create comprehensive, well-structured study notes in Simplified Chinese.

Please integrate information from the images (slides, charts) with the transcript text to provide a complete picture.

Sections to include:
1. **课程摘要 (Summary)**: A high-level overview of the video's content.
2. **核心概念 (Key Concepts)**: Detailed explanations of professional terms and theories mentioned. Reference the slides if they contain definitions or charts.
3. **重要公式 (Important Formulas)**: List any formulas mentioned with variable definitions.
4. **考试重点 (Exam Focus)**: Specific tips or areas that are likely to appear on the CFA exam.
5. **中英术语对照 (Terminology Table)**: A table of technical terms used in the video.
"""

    text_prompt = f"### Transcript:\n{truncated}"

    # Build content array; attach images if available
    user_content: list = [{"type": "text", "text": text_prompt}]
    frame_links = ""
    if frame_paths:
        print(f"  [Study Notes] Processing {len(frame_paths)} keyframes...")
        frame_links = "\n\n### 課程投影片回顧\n"
        for i, fp in enumerate(frame_paths, 1):
            if not fp.exists(): continue
            frame_links += f"![投影片 {i}](frames/{fp.name})\n"
            try:
                img_bytes = _compress_image(fp)
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                })
            except Exception as e:
                print(f"  [Study Notes] Failed to attach {fp.name}: {e}")

    def _call(content):
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
        )

    try:
        from usage_tracker import check_backoff  # type: ignore
        check_backoff()
        res = _call(user_content)
    except Exception as e:
        if frame_paths:
            # Model may not support images — retry text-only
            print(f"  [Study Notes] Image call failed ({e}), retrying text-only...")
            try:
                res = _call(text_prompt)
            except Exception as e2:
                print(f"  [Study Notes] Critical Failure: {e2}")
                from usage_tracker import log_failure  # type: ignore
                log_failure("Notes", v_name, str(e2))
                raise e2
        else:
            print(f"  [Study Notes] Critical Failure: {e}")
            from usage_tracker import log_failure  # type: ignore
            log_failure("Notes", v_name, str(e))
            raise e

    if res.usage:
        log_usage("Notes", v_name, res.usage.prompt_tokens, res.usage.completion_tokens, model=model)
        print(f"  Token Usage (Notes): Input={res.usage.prompt_tokens}, Output={res.usage.completion_tokens}")

    response_text = (res.choices[0].message.content or "").strip()

    try:
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        notes_content = f"# CFA Study Notes: {v_name}\n\n" + response_text
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
