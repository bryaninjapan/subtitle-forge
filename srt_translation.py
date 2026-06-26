"""Translation response parsing and batch formatting for SRT entries."""
import json
import re
from typing import Any

from srt_utils import SrtEntry


def format_batch_for_translation(
    batch: list[SrtEntry], context: list[SrtEntry] | None = None
) -> str:
    """Format a batch of SRT entries into a string for the translation API."""
    lines = []
    if context:
        lines.append("### Context (Reference only, do not translate):")
        for e in context:
            lines.append(f"REF|{e.text}")
        lines.append("### Content to translate:")
    for e in batch:
        lines.append(f"{e.index}|{e.text}")
    return "\n".join(lines)


def parse_translation_response(
    response: str, batch: list[SrtEntry]
) -> list[str]:
    """Parse the API response into a list of translated texts matching the batch order."""
    translations: dict[int, str] = {}

    # 1. Clean response of markdown markers
    clean_json = re.sub(
        r"```(?:json)?\s*(.*?)\s*```", r"\1", response, flags=re.DOTALL
    ).strip()

    try:
        data = json.loads(clean_json)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    idx = item.get("index")
                    txt = (
                        item.get("text")
                        or item.get("translation")
                        or item.get("translated_text")
                    )
                    if idx is not None and txt:
                        translations[int(idx)] = str(txt).strip()
        elif isinstance(data, dict):
            items = data.get("translations") or data.get("data") or data
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        idx = item.get("index") or item.get("id")
                        txt = item.get("text") or item.get("translation")
                        if idx is not None and txt:
                            translations[int(idx)] = str(txt).strip()
            elif isinstance(items, dict):
                for k, v in items.items():
                    try:
                        translations[int(k)] = str(v).strip()
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        print(f"  [DEBUG] JSON Parse failed: {e}. Attempting regex recovery.")

    # 2. Regex fallbacks
    if not translations:
        for line in response.splitlines():
            m = re.search(r"(\d+)\s*[\|:]\s*(.+)", line)
            if m:
                translations[int(m.group(1))] = m.group(2).strip()
        if not translations:
            idx_matches = re.finditer(
                r'[\"\']?index[\"\']?:\s*(\d+)', clean_json
            )
            txt_matches = re.finditer(
                r'[\"\']?(?:text|translation)[\"\']?:\s*[\"\'](.*?)[\"\'](?=,|\s*\})',
                clean_json,
            )
            for im, tm in zip(idx_matches, txt_matches):
                translations[int(im.group(1))] = tm.group(1).strip()

    return [translations.get(e.index, e.text) for e in batch]
