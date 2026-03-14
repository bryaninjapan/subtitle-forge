import json
import os
from pathlib import Path
from google import genai
from google.genai import types

def extract_terms_with_ai(transcript_text: str, current_glossary: dict) -> dict:
    """Ask Gemini to identify key financial terms and suggest translations."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {}
        
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash") # Use a fast model for scanning

    # Prepare current terms to avoid duplicates or conflicts
    existing_keys = ", ".join(current_glossary.keys())
    
    prompt = f"""
You are a financial terminology expert. Analyze the following transcript of a CFA Level 1 lecture.
Identify the top 10 most important technical terms or abbreviations that are NOT in this list: [{existing_keys}].

Provide professional Traditional Chinese (Taiwan) translations for these specific terms.
Output ONLY a valid JSON object where keys are English terms and values are Chinese translations.

Transcript:
{transcript_text[:10000]} # Send a significant portion for context
"""
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
        )
        new_terms = json.loads(response.text)
        return new_terms
    except Exception as e:
        print(f"  [Glossary] AI scanning failed: {e}")
        return {}

def update_glossary_auto(srt_path: Path):
    """Scan the transcript and update glossary.json with new found terms."""
    from config import GLOSSARY_PATH, load_glossary
    
    # 1. Read plain text version if available, else derive from srt
    txt_path = srt_path.with_suffix(".txt")
    if txt_path.exists():
        text = txt_path.read_text(encoding="utf-8")
    else:
        # Fallback to simple SRT text extraction
        import re
        content = srt_path.read_text(encoding="utf-8")
        text = " ".join(re.findall(r"\n([^\d\n].*)\n", content))

    if not text:
        return

    # 2. Load current
    current = load_glossary()
    
    # 3. Get new terms from AI
    print(f"  [Glossary] Scanning '{srt_path.name}' for new financial terms...")
    new_terms = extract_terms_with_ai(text, current)
    
    if new_terms:
        # 4. Merge
        added_count = 0
        for k, v in new_terms.items():
            if k not in current:
                current[k] = v
                added_count += 1
                print(f"    + New term: {k} -> {v}")
        
        if added_count > 0:
            # 5. Save back to file
            GLOSSARY_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=4), encoding="utf-8")
            print(f"  [Glossary] Automatically added {added_count} new terms to glossary.json")
