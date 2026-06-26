import json
import os
import threading
from pathlib import Path
from google.genai import types
from config import DEFAULT_GEMINI_MODEL, GLOSSARY_PATH, load_glossary, GLOSSARY_EXTRACTION_PROMPT
from gemini_client import get_gemini_client

_glossary_lock = threading.Lock()

def _get_gemini_client():
    return get_gemini_client()

def load_glossary_raw() -> dict:
    """Load the raw dictionary including metadata (hits)."""
    if not GLOSSARY_PATH.exists(): return {}
    try:
        data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
        # Standardize format: {term: {"val": "trans", "hits": N}}
        standardized = {}
        for k, v in data.items():
            if isinstance(v, dict): standardized[k] = v
            else: standardized[k] = {"val": v, "hits": 0}
        return standardized
    except (json.JSONDecodeError, OSError): return {}

def save_glossary_raw(data: dict):
    """Save sorted raw dictionary."""
    sorted_data = dict(sorted(data.items()))
    GLOSSARY_PATH.write_text(json.dumps(sorted_data, ensure_ascii=False, indent=4), encoding="utf-8")
    load_glossary.cache_clear()

def record_term_hits(terms_used: list[str]):
    """Increment hit counters for terms used in a batch."""
    with _glossary_lock:
        raw = load_glossary_raw()
        for t in terms_used:
            if t in raw:
                raw[t]["hits"] = raw[t].get("hits", 0) + 1
        save_glossary_raw(raw)

def prune_glossary(min_hits: int = 2):
    """Remove terms with very low usage to keep prompt clean."""
    with _glossary_lock:
        raw = load_glossary_raw()
        before = len(raw)
        raw = {k: v for k, v in raw.items() if v.get("hits", 0) >= min_hits}
        after = len(raw)
        if before != after:
            save_glossary_raw(raw)
            print(f"  [Glossary] Pruned {before - after} low-usage terms.")

def extract_terms_with_ai(transcript_text: str, current_glossary: dict) -> dict:
    client = _get_gemini_client()
    if not client: return {}
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    existing_keys = ", ".join(current_glossary.keys())
    
    prompt = GLOSSARY_EXTRACTION_PROMPT.replace("{existing_keys}", existing_keys) + f"\nText:\n{transcript_text[:5000]}"
    try:
        res = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")
        )
        return json.loads(res.text)
    except (json.JSONDecodeError, OSError): return {}

def update_glossary_auto(srt_path: Path):
    with _glossary_lock:
        raw = load_glossary_raw()
        current = {k: v["val"] for k, v in raw.items()}
        
        txt_p = srt_path.with_suffix(".txt")
        text = txt_p.read_text(encoding="utf-8") if txt_p.exists() else ""
        if not text: return

        new_terms = extract_terms_with_ai(text, current)
        if new_terms:
            added = 0
            for k, v in new_terms.items():
                if k not in raw:
                    raw[k] = {"val": v, "hits": 1} # Start with 1 hit as it was found in transcript
                    added += 1
            if added > 0:
                save_glossary_raw(raw)
                print(f"  [Glossary] Added {added} new terms.")
