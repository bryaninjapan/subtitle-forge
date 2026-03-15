"""SRT subtitle parsing, batching, and writing utilities."""

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
    """Parse SRT content string into a list of SrtEntry objects."""
    entries: list[SrtEntry] = []
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1].strip(),
        )
        if not time_match:
            continue
        text = "\n".join(lines[2:]).strip()
        entries.append(SrtEntry(
            index=index,
            start=time_match.group(1),
            end=time_match.group(2),
            text=text,
        ))
    return entries


def normalize_srt(entries: list[SrtEntry]) -> list[SrtEntry]:
    """Ensure entries have sequential indices and valid time formats."""
    normalized: list[SrtEntry] = []
    for i, entry in enumerate(entries, 1):
        # Ensure timestamp format is HH:MM:SS,mmm
        def fix_time(t: str) -> str:
            t = t.replace(".", ",")
            parts = t.split(":")
            if len(parts) == 2:  # MM:SS,mmm
                t = f"00:{t}"
            return t

        normalized.append(SrtEntry(
            index=i,
            start=fix_time(entry.start),
            end=fix_time(entry.end),
            text=entry.text.strip()
        ))
    return normalized


def write_srt(entries: list[SrtEntry], path: Path) -> None:
    """Write a list of SrtEntry objects to an SRT file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_srt(entries)
    with open(path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(normalized):
            if i > 0:
                f.write("\n")
            f.write(f"{entry.index}\n")
            f.write(f"{entry.start} --> {entry.end}\n")
            f.write(f"{entry.text}\n")


def entries_to_srt_string(entries: list[SrtEntry]) -> str:
    """Convert a list of SrtEntry objects to SRT format string."""
    parts: list[str] = []
    for entry in entries:
        parts.append(f"{entry.index}\n{entry.start} --> {entry.end}\n{entry.text}")
    return "\n\n".join(parts) + "\n"


def batch_entries(entries: list[SrtEntry], batch_size: int) -> list[list[SrtEntry]]:
    """Split entries into batches for translation."""
    return [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]


def format_batch_for_translation(batch: list[SrtEntry], context: list[SrtEntry] | None = None) -> str:
    """Format a batch of SRT entries for the translation prompt.

    If context is provided, it is prepended as read-only reference to help 
    the model maintain consistency across batches.
    """
    lines = []
    if context:
        lines.append("### 上文參考 (僅供語境參考，不用翻譯以下內容):")
        for e in context:
            lines.append(f"REF|{e.text}")
        lines.append("### 正文翻譯 (請開始翻譯以下內容):")

    for e in batch:
        lines.append(f"{e.index}|{e.text}")
        
    return "\n".join(lines)


def parse_translation_response(response: str, batch: list[SrtEntry]) -> list[str]:
    """Parse the translation model's response back into per-entry translations.

    Expected response format (one per line):
        1|翻譯文字
        2|另一行翻譯

    Falls back to line-by-line matching if parsing fails.
    """
    lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
    translations: dict[int, str] = {}

    for line in lines:
        match = re.match(r"(\d+)\s*\|\s*(.+)", line)
        if match:
            idx = int(match.group(1))
            translations[idx] = match.group(2).strip()

    result: list[str] = []
    for entry in batch:
        if entry.index in translations:
            result.append(translations[entry.index])
        else:
            result.append(entry.text)  # fallback: keep original

    return result
