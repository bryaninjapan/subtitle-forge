"""SRT subtitle parsing, batching, and writing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

@dataclass
class SrtEntry:
    index: int
    start: str  # "HH:MM:SS,mmm"
    end: str
    text: str

def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds (float) to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt(content: str) -> list[SrtEntry]:
    """Parse SRT content string into a list of SrtEntry objects with lenient timestamp matching."""
    entries: list[SrtEntry] = []
    # 1. Clean response
    content = re.sub(r"```[a-z]*\n", "", content)
    content = content.replace("```", "").strip()
    content = content.replace("\r\n", "\n")
    
    # 2. Split by empty lines or common pattern gaps
    blocks = re.split(r"\n\s*\n", content)
    
    # Helper to normalize timestamps (HH:MM:SS,mmm)
    def normalize_timestamp(t: str) -> str:
        # 1. Split by non-digit characters to get numeric parts
        parts = re.split(r"[^0-9]", t.strip())
        parts = [p for p in parts if p]
        
        # We need to map these to h, m, s, ms
        h, m, s, ms = 0, 0, 0, 0
        
        if len(parts) == 4:
            # HH:MM:SS:mmm
            h, m, s, ms = map(int, parts)
        elif len(parts) == 3:
            # Could be HH:MM:SS or MM:SS:mmm
            # Heuristic: if the last part is > 59 or has 3 digits, it's probably ms
            if int(parts[2]) > 59 or len(parts[2]) == 3:
                m, s, ms = map(int, parts)
            else:
                h, m, s = map(int, parts)
        elif len(parts) == 2:
            # MM:SS or SS:mmm
            if int(parts[1]) > 59 or len(parts[1]) == 3:
                s, ms = map(int, parts)
            else:
                m, s = map(int, parts)
        elif len(parts) == 1:
            s = int(parts[0])
            
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines: continue
        
        # Look for the time line (usually at index 0 or 1)
        time_line_idx = -1
        for i, line in enumerate(lines[:3]):  # type: ignore
            if "-->" in line:
                time_line_idx = i
                break
        
        if time_line_idx == -1: continue
        
        try:
            time_line = lines[time_line_idx].strip()  # type: ignore
            # Strip leading index number if present on same line as timestamp (e.g. "1 00:06:290 --> ...")
            time_line = re.sub(r"^\d+\s+", "", time_line)
            time_parts = [p.strip() for p in time_line.split("-->")]
            if len(time_parts) != 2: continue

            start_raw, end_raw = time_parts
            
            # Identify text
            text = "\n".join(lines[time_line_idx+1:]).strip()  # type: ignore
            if not text: continue
            
            # Identify index (line above time_line if it exists and is digits)
            index = len(entries) + 1
            if time_line_idx > 0:
                idx_match = re.match(r"^(\d+)$", lines[time_line_idx-1].strip())  # type: ignore
                if idx_match:
                    index = int(idx_match.group(1))

            start_ts = normalize_timestamp(start_raw)
            end_ts = normalize_timestamp(end_raw)
            
            # Fix: Ensure start <= end
            if _srt_time_to_seconds(start_ts) > _srt_time_to_seconds(end_ts):
                end_ts = seconds_to_srt_time(_srt_time_to_seconds(start_ts) + 2.0)

            entries.append(SrtEntry(
                index=index,
                start=start_ts,
                end=end_ts,
                text=text,
            ))
        except (ValueError, IndexError, Exception):
            continue
            
    return entries

def normalize_srt(entries: list[SrtEntry]) -> list[SrtEntry]:
    """Ensure sequential indices, correct formats, and fix overlaps."""
    if not entries: return []
    
    # 1. Basic formatting
    res: list[SrtEntry] = []
    for i, e in enumerate(entries, 1):
        def fix_t(t: str) -> str:
            t = t.replace(".", ",")
            parts = t.split(":")
            if len(parts) == 2: t = f"00:{t}"
            if len(parts[0]) == 1: t = f"0{t}"
            return t
        res.append(SrtEntry(i, fix_t(e.start), fix_t(e.end), e.text.strip()))
    
    # 2. Fix overlaps (Ensure chronological order)
    for i in range(1, len(res)):
        prev = res[i-1]
        curr = res[i]
        
        p_end = _srt_time_to_seconds(prev.end)
        c_start = _srt_time_to_seconds(curr.start)
        
        if c_start < p_end:
            # Overlap detected! Set prev end to curr start - 10ms
            new_end_sec = max(0.0, c_start - 0.01)
            prev.end = seconds_to_srt_time(new_end_sec)
            
    return res

def write_srt(entries: list[SrtEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    res = normalize_srt(entries)
    with open(path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(res):
            if i > 0: f.write("\n")
            f.write(f"{entry.index}\n{entry.start} --> {entry.end}\n{entry.text}\n")

def convert_srt_to_vtt(srt_path: Path, vtt_path: Path) -> None:
    """Convert SRT file to WebVTT format."""
    content = srt_path.read_text(encoding="utf-8")
    vtt_content = "WEBVTT\n\n" + content.replace(",", ".")
    vtt_path.write_text(vtt_content, encoding="utf-8")

def create_bilingual_srt(en_entries: list[SrtEntry], zh_entries: list[SrtEntry], output_path: Path) -> None:
    """Merge EN and ZH entries into a single bilingual SRT."""
    if len(en_entries) != len(zh_entries):
        zh_map = {e.index: e.text for e in zh_entries}
        merged = [SrtEntry(en.index, en.start, en.end, f"{en.text}\n{zh_map.get(en.index, '')}") for en in en_entries]
        write_srt(merged, output_path)
    else:
        merged = [
            SrtEntry(en.index, en.start, en.end, f"{en.text}\n{zh.text}")
            for en, zh in zip(en_entries, zh_entries)
        ]
        write_srt(merged, output_path)

def validate_srt_completeness(original_path: Path, translated_path: Path) -> bool:
    """Check if translated SRT has same number of entries as original."""
    try:
        orig = parse_srt(original_path.read_text(encoding="utf-8"))
        trans = parse_srt(translated_path.read_text(encoding="utf-8"))
        return len(orig) == len(trans)
    except: return False

def split_monolithic_entry(entry: SrtEntry, words_per_second: float = 2.2, chunk_words: int = 15) -> list[SrtEntry]:
    """Split a single oversized SRT entry into multiple timed entries with synthetic timestamps.

    Uses sentence boundaries where possible, falls back to word chunks.
    Timestamps are estimated at the given speaking rate starting from entry.start.
    """
    text = entry.text.strip()
    start_sec = _srt_time_to_seconds(entry.start)

    # Split by sentence-ending punctuation
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)

    # Group short sentences; break long ones into word chunks
    chunks: list[str] = []
    buffer = ""
    for sent in raw_sentences:
        candidate = (buffer + " " + sent).strip() if buffer else sent
        if len(candidate.split()) <= chunk_words * 2:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            words = sent.split()
            for i in range(0, len(words), chunk_words):
                chunks.append(" ".join(words[i:i + chunk_words]))  # type: ignore[index]
            buffer = ""
    if buffer:
        chunks.append(buffer)

    entries: list[SrtEntry] = []
    cur_sec = start_sec
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        word_count = len(chunk.split())
        duration = max(1.5, word_count / words_per_second)
        end_sec = cur_sec + duration
        entries.append(SrtEntry(
            index=i + 1,
            start=seconds_to_srt_time(cur_sec),
            end=seconds_to_srt_time(end_sec),
            text=chunk.strip(),
        ))
        cur_sec = end_sec

    return entries


def batch_entries(entries: list[SrtEntry], batch_size: int = 50, max_gap: float = 1.5) -> list[list[SrtEntry]]:
    if not entries: return []
    batches, current_batch = [], []
    for i, entry in enumerate(entries):
        current_batch.append(entry)
        should_split = False
        if len(current_batch) >= batch_size:
            should_split = True
            if i + 1 < len(entries):
                try:
                    this_end = _srt_time_to_seconds(entry.end)
                    nxt_start = _srt_time_to_seconds(entries[i+1].start)
                    if nxt_start - this_end < max_gap and len(current_batch) < (batch_size + 15):
                        should_split = False
                except: pass
        if should_split:
            batches.append(current_batch); current_batch = []
    if current_batch: batches.append(current_batch)
    return batches

def _srt_time_to_seconds(t: str) -> float:
    try:
        h, m, s_ms = t.replace(",", ".").split(":")
        return int(h)*3600 + int(m)*60 + float(s_ms)
    except: return 0.0

def clean_subtitle_text(text: str) -> str:
    """Clean subtitle text: remove only SDH noise, NOT speaker labels or real content."""
    if not text: return ""
    # Remove known SDH/formatting noise only (music notes, pure symbol brackets)
    text = re.sub(r'[♪♫]', '', text)
    text = re.sub(r'\[(?i:music|applause|laughter|noise|silence|audio)\]', '', text)
    text = re.sub(r'\(\s*[^)]{0,30}\s*\)', '', text)  # Only short parenthetical notes
    # Remove leading markdown/quote chars
    text = re.sub(r'^[>\-\s\.]+', '', text)
    cleaned = re.sub(r'\s+', ' ', text).strip()
    # Safety: if cleaning produced empty string, return original stripped
    return cleaned if cleaned else text.strip()

def format_batch_for_translation(batch: list[SrtEntry], context: list[SrtEntry] | None = None) -> str:
    lines = []
    if context:
        lines.append("### Context (Reference only, do not translate):")
        for e in context: lines.append(f"REF|{e.text}")
        lines.append("### Content to translate:")
    for e in batch: lines.append(f"{e.index}|{e.text}")
    return "\n".join(lines)

def parse_translation_response(response: str, batch: list[SrtEntry]) -> list[str]:
    import json
    import re
    translations: dict[int, str] = {}
    
    # 1. Clean response of markdown markers
    clean_json = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', response, flags=re.DOTALL).strip()
    
    try:
        data = json.loads(clean_json)
        # Handle list of objects: [{"index": 1, "text": "..."}, ...]
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    idx = item.get("index")
                    txt = item.get("text") or item.get("translation") or item.get("translated_text")
                    if idx is not None and txt:
                        translations[int(idx)] = str(txt).strip()
        # Handle dict: {"1": "...", "2": "..."} or {"translations": [...]}
        elif isinstance(data, dict):
            items = data.get("translations") or data.get("data") or data
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        idx = item.get("index") or item.get("id")
                        txt = item.get("text") or item.get("translation")
                        if idx is not None and txt: translations[int(idx)] = str(txt).strip()
            elif isinstance(items, dict):
                for k, v in items.items():
                    try: translations[int(k)] = str(v).strip()
                    except: pass
    except Exception as e:
        print(f"  [DEBUG] JSON Parse failed: {e}. Attempting regex recovery.")

    # 2. Regex fallbacks for non-JSON or weird formats
    if not translations:
        # Match format: 1 | 翻譯文本
        for line in response.splitlines():
            m = re.search(r"(\d+)\s*[\|:]\s*(.+)", line)
            if m: translations[int(m.group(1))] = m.group(2).strip()
        # Match "index": 1, "text": "翻譯"
        if not translations:
            idx_matches = re.finditer(r'[\"\']?index[\"\']?:\s*(\d+)', clean_json)
            txt_matches = re.finditer(r'[\"\']?(?:text|translation)[\"\']?:\s*[\"\'](.*?)[\"\'](?=,|\s*\})', clean_json)
            for im, tm in zip(idx_matches, txt_matches):
                translations[int(im.group(1))] = tm.group(1).strip()

    return [translations.get(e.index, e.text) for e in batch]

def create_bilingual_srt_from_text(raw_srt_text: str, zh_srt_text: str, working_directory: str) -> Dict[str, Any]:
    """Agent wrapper for creating bilingual SRT files."""
    from pathlib import Path
    w_d = Path(working_directory)
    
    en_entries = parse_srt(raw_srt_text)
    zh_entries = parse_srt(zh_srt_text)
    
    bi_srt_p = w_d / f"{w_d.name}.bilingual.srt"
    create_bilingual_srt(en_entries, zh_entries, bi_srt_p)
    
    return {
        "bilingual_srt_text": bi_srt_p.read_text(encoding="utf-8"),
        "bilingual_srt_path": str(bi_srt_p)
    }

