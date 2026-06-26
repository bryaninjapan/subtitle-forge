"""Bilingual SRT creation — merge EN and ZH subtitle entries."""
from pathlib import Path
from typing import Any, Dict

from srt_utils import SrtEntry, parse_srt, write_srt


def create_bilingual_srt(
    en_entries: list[SrtEntry],
    zh_entries: list[SrtEntry],
    output_path: Path,
) -> None:
    """Merge EN and ZH entries into a single bilingual SRT."""
    if len(en_entries) != len(zh_entries):
        zh_map = {e.index: e.text for e in zh_entries}
        merged = [
            SrtEntry(en.index, en.start, en.end, f"{en.text}\n{zh_map.get(en.index, '')}")
            for en in en_entries
        ]
        write_srt(merged, output_path)
    else:
        merged = [
            SrtEntry(en.index, en.start, en.end, f"{en.text}\n{zh.text}")
            for en, zh in zip(en_entries, zh_entries)
        ]
        write_srt(merged, output_path)


def create_bilingual_srt_from_text(
    raw_srt_text: str, zh_srt_text: str, working_directory: str
) -> Dict[str, Any]:
    """Agent wrapper for creating bilingual SRT files."""
    w_d = Path(working_directory)

    en_entries = parse_srt(raw_srt_text)
    zh_entries = parse_srt(zh_srt_text)

    bi_srt_p = w_d / f"{w_d.name}.bilingual.srt"
    create_bilingual_srt(en_entries, zh_entries, bi_srt_p)

    return {
        "bilingual_srt_text": bi_srt_p.read_text(encoding="utf-8"),
        "bilingual_srt_path": str(bi_srt_p),
    }
