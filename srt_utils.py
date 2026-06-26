"""
SRT subtitle parsing, batching, and writing utilities.

Note: bilingual and translation-parse functions moved to
srt_bilingual.py and srt_translation.py respectively.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


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
        parts = re.split(r"[^0-9]", t.strip())
        parts = [p for p in parts if p]
        h, m, s, ms = 0, 0, 0, 0
        if len(parts) == 4:
            h, m, s, ms = map(int, parts)
        elif len(parts) == 3:
            if int(parts[2]) > 59 or len(parts[2]) == 3:
                m, s, ms = map(int, parts)
            else:
                h, m, s = map(int, parts)
        elif len(parts) == 2:
            if int(parts[1]) > 59 or len(parts[1]) == 3:
                s, ms = map(int, parts)
            else:
                m, s = map(int, parts)
        elif len(parts) == 1:
            s = int(parts[0])
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        time_line_idx = -1
        for i, line in enumerate(lines[:3]):
            if "-->" in line:
                time_line_idx = i
                break
        if time_line_idx == -1:
            continue

        try:
            time_line = lines[time_line_idx].strip()
            time_line = re.sub(r"^\d+\s+", "", time_line)
            time_parts = [p.strip() for p in time_line.split("-->")]
            if len(time_parts) != 2:
                continue

            start_raw, end_raw = time_parts
            text = "\n".join(lines[time_line_idx + 1 :]).strip()
            if not text:
                continue

            index = len(entries) + 1
            if time_line_idx > 0:
                idx_match = re.match(r"^(\d+)$", lines[time_line_idx - 1].strip())
                if idx_match:
                    index = int(idx_match.group(1))

            start_ts = normalize_timestamp(start_raw)
            end_ts = normalize_timestamp(end_raw)

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
    if not entries:
        return []
    res: list[SrtEntry] = []
    for i, e in enumerate(entries, 1):
        def fix_t(t: str) -> str:
            t = t.replace(".", ",")
            parts = t.split(":")
            if len(parts) == 2:
                t = f"00:{t}"
            if len(parts[0]) == 1:
                t = f"0{t}"
            return t
        res.append(SrtEntry(i, fix_t(e.start), fix_t(e.end), e.text.strip()))

    for i in range(1, len(res)):
        prev = res[i - 1]
        curr = res[i]
        p_end = _srt_time_to_seconds(prev.end)
        c_start = _srt_time_to_seconds(curr.start)
        if c_start < p_end:
            new_end_sec = max(0.0, c_start - 0.01)
            prev.end = seconds_to_srt_time(new_end_sec)

    return res


def write_srt(entries: list[SrtEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    res = normalize_srt(entries)
    with open(path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(res):
            if i > 0:
                f.write("\n")
            f.write(f"{entry.index}\n{entry.start} --> {entry.end}\n{entry.text}\n")


def convert_srt_to_vtt(srt_path: Path, vtt_path: Path) -> None:
    """Convert SRT file to WebVTT format."""
    content = srt_path.read_text(encoding="utf-8")
    vtt_content = "WEBVTT\n\n" + content.replace(",", ".")
    vtt_path.write_text(vtt_content, encoding="utf-8")


def validate_srt_completeness(original_path: Path, translated_path: Path) -> bool:
    """Check if translated SRT has same number of entries as original."""
    try:
        orig = parse_srt(original_path.read_text(encoding="utf-8"))
        trans = parse_srt(translated_path.read_text(encoding="utf-8"))
        return len(orig) == len(trans)
    except Exception:
        return False


def split_monolithic_entry(
    entry: SrtEntry, words_per_second: float = 2.2, chunk_words: int = 15
) -> list[SrtEntry]:
    """Split a single oversized SRT entry into multiple timed entries."""
    text = entry.text.strip()
    start_sec = _srt_time_to_seconds(entry.start)
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)

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
                chunks.append(" ".join(words[i : i + chunk_words]))
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


def batch_entries(
    entries: list[SrtEntry], batch_size: int = 50, max_gap: float = 1.5
) -> list[list[SrtEntry]]:
    if not entries:
        return []
    batches, current_batch = [], []
    for i, entry in enumerate(entries):
        current_batch.append(entry)
        should_split = False
        if len(current_batch) >= batch_size:
            should_split = True
            if i + 1 < len(entries):
                try:
                    this_end = _srt_time_to_seconds(entry.end)
                    nxt_start = _srt_time_to_seconds(entries[i + 1].start)
                    if nxt_start - this_end < max_gap and len(current_batch) < (batch_size + 15):
                        should_split = False
                except (ValueError, TypeError):
                    pass
        if should_split:
            batches.append(current_batch)
            current_batch = []
    if current_batch:
        batches.append(current_batch)
    return batches


def _srt_time_to_seconds(t: str) -> float:
    try:
        h, m, s_ms = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s_ms)
    except (ValueError, AttributeError):
        return 0.0


def clean_subtitle_text(text: str) -> str:
    """Clean subtitle text: remove only SDH noise, NOT speaker labels or real content."""
    if not text:
        return ""
    text = re.sub(r"[♪♫]", "", text)
    text = re.sub(r"\[(?i:music|applause|laughter|noise|silence|audio)\]", "", text)
    text = re.sub(r"\(\s*[^)]{0,30}\s*\)", "", text)
    text = re.sub(r"^[>\-\s\.]+", "", text)
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else text.strip()
