import json
import os
import threading
from pathlib import Path
from config import OPENROUTER_TEXT_MODEL, GLOSSARY_PATH, load_glossary
from openrouter_client import get_openrouter_client

_glossary_lock = threading.Lock()

def load_glossary_raw() -> dict:
    """Load the raw dictionary including metadata (hits)."""
    if not GLOSSARY_PATH.exists(): return {}
    try:
        data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
        standardized = {}
        for k, v in data.items():
            if isinstance(v, dict): standardized[k] = v
            else: standardized[k] = {"val": v, "hits": 0}
        return standardized
    except: return {}

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
    try:
        client = get_openrouter_client()
        model = os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL)
        existing_keys = ", ".join(current_glossary.keys())

        system = "You are a CFA terminology extractor. Output ONLY valid JSON with no explanation, no markdown fences."
        prompt = (
            f"Identify 5-10 technical CFA terms NOT already in: [{existing_keys}].\n"
            f"Output JSON object: {{\"term\": \"chinese_translation\"}}\n"
            f"Text:\n{transcript_text[:5000]}"
        )
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        text = (res.choices[0].message.content or "").strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {}

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
                    raw[k] = {"val": v, "hits": 1}
                    added += 1
            if added > 0:
                save_glossary_raw(raw)
                print(f"  [Glossary] Added {added} new terms.")
