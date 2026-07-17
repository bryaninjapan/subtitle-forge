#!/usr/bin/env python3
"""
recover — Universal detect-and-fix engine for incomplete pipeline outputs.

Zero API calls. Scans all output dirs, classifies gaps into a task grid,
fixes everything local-fixable, then reports what still needs the API.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from config import OUTPUT_DIR  # type: ignore
from srt_bilingual import create_bilingual_srt  # type: ignore
from srt_utils import (  # type: ignore
    convert_srt_to_vtt,
    parse_srt,
    split_monolithic_entry,
    write_srt,
)

_MONOLITHIC_MAX_ENTRY_CHARS = 2_000

# ─────────────────────────── Gap Scanner ─────────────────────────────────────


def scan_gaps(output_dir: Path) -> dict[str, list[Path]]:
    """Scan all output subdirs and classify gaps into recoverable categories."""
    gaps: dict[str, list[Path]] = {
        "D_monolithic": [],
        "B_transcript": [],
        "C_naming": [],
        "A_bilingual": [],
        "needs_translation": [],
        "needs_asr": [],
        "needs_notes": [],
    }
    if not output_dir.exists():
        return gaps
    for task_dir in sorted(output_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        srt = task_dir / f"{task_dir.name}.srt"
        zh_srt = task_dir / f"{task_dir.name}.zh.srt"
        bilingual = task_dir / f"{task_dir.name}.bilingual.srt"
        old_srt = task_dir / "subtitle.srt"
        transcript = task_dir / "transcript.txt"
        notes = task_dir / "studynotes.md"

        if srt.exists() and zh_srt.exists() and not bilingual.exists():
            gaps["A_bilingual"].append(task_dir)
            continue

        if transcript.exists() and not srt.exists():
            gaps["B_transcript"].append(task_dir)
            continue

        if not srt.exists() and old_srt.exists():
            gaps["C_naming"].append(task_dir)
            continue

        if srt.exists() and not zh_srt.exists():
            gaps["needs_translation"].append(task_dir)
            continue

        if srt.exists() and zh_srt.exists() and not notes.exists():
            gaps["needs_notes"].append(task_dir)
            continue

        if not srt.exists():
            gaps["needs_asr"].append(task_dir)
            continue

    # Post-scan: check for monolithic SRT entries (needs D)
    for task_dir in sorted(output_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        srt = task_dir / f"{task_dir.name}.srt"
        vtt = task_dir / f"{task_dir.name}.vtt"
        if srt.exists():
            try:
                entries = parse_srt(srt)
                for entry in entries:
                    if len(entry.text) > _MONOLITHIC_MAX_ENTRY_CHARS:
                        gaps["D_monolithic"].append(task_dir)
                        break
            except Exception:
                pass
        if vtt.exists():
            try:
                text = vtt.read_text(encoding="utf-8")
                if any(
                    len(block) > _MONOLITHIC_MAX_ENTRY_CHARS
                    for block in text.split("\n\n")[1:]
                ):
                    if task_dir not in gaps["D_monolithic"]:
                        gaps["D_monolithic"].append(task_dir)
            except Exception:
                pass

    return gaps


# ─────────────────────────── Fixers ──────────────────────────────────────────


def _strip_hallucination_tail(
    text: str, window: int = 400, repeat_threshold: float = 0.5
) -> str:
    """Detect and strip repeating hallucination tails from SRT text."""

    def _is_hallucination(segment: str) -> bool:
        """Heuristic: many repeated words or chars = stuck/hallucination."""
        if not segment.strip():
            return False
        words = segment.split()
        if not words:
            return False
        unique = len(set(words))
        return unique / len(words) < repeat_threshold

    if len(text) < window * 2:
        return text
    for offset in range(window, len(text) - window):
        chunk = text[offset: offset + window]
        if _is_hallucination(chunk):
            return text[:offset]
    return text


def recover_transcripts(dirs: list[Path]) -> tuple[int, list[Path]]:
    """Convert transcript.txt → SRT for gap B dirs."""
    fixed = 0
    failed: list[Path] = []
    for task_dir in dirs:
        srt = task_dir / f"{task_dir.name}.srt"
        transcript = task_dir / "transcript.txt"
        if not transcript.exists():
            failed.append(task_dir)
            continue
        raw = transcript.read_text(encoding="utf-8", errors="replace")
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        entries = []
        for i, text in enumerate(lines, 1):
            from datetime import timedelta

            start = timedelta(seconds=(i - 1) * 3)
            end = timedelta(seconds=i * 3)
            entries.append(
                f"{i}\n{_td_to_srt(start)} --> {_td_to_srt(end)}\n{text}\n"
            )
        srt.write_text("\n".join(entries), encoding="utf-8")
        fixed += 1
    return fixed, failed


def _td_to_srt(td) -> str:
    h, remainder = divmod(int(td.total_seconds()), 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d},000"


def recover_monolithic(dirs: list[Path]) -> tuple[int, list[Path]]:
    """Split monolithic SRT entries for gap D dirs."""
    fixed = 0
    failed: list[Path] = []
    for task_dir in dirs:
        srt = task_dir / f"{task_dir.name}.srt"
        vtt = task_dir / f"{task_dir.name}.vtt"
        if srt.exists():
            try:
                entries = parse_srt(srt)
                new_entries = []
                for entry in entries:
                    if len(entry.text) > _MONOLITHIC_MAX_ENTRY_CHARS:
                        split = split_monolithic_entry(entry, max_chars=200)
                        new_entries.extend(split)
                    else:
                        new_entries.append(entry)
                write_srt(srt, new_entries)
                fixed += 1
            except Exception:
                failed.append(task_dir)
        if vtt.exists():
            convert_srt_to_vtt(srt, vtt) if srt.exists() else None
    return fixed, failed


def recover_seminar_naming(dirs: list[Path]) -> tuple[int, list[Path]]:
    """Rename subtitle.srt → {task}.srt for gap C dirs."""
    fixed = 0
    failed: list[Path] = []
    for task_dir in dirs:
        old = task_dir / "subtitle.srt"
        new = task_dir / f"{task_dir.name}.srt"
        if old.exists():
            shutil.move(str(old), str(new))
            fixed += 1
        else:
            failed.append(task_dir)
    return fixed, failed


def recover_bilingual(
    output_dir: Path, target_dirs: list[Path] | None = None
) -> tuple[int, int]:
    """Create bilingual SRT for gap A dirs."""
    fixed = 0
    total = 0
    candidates = target_dirs or [
        d for d in sorted(output_dir.iterdir()) if d.is_dir()
    ]
    for task_dir in candidates:
        srt = task_dir / f"{task_dir.name}.srt"
        zh = task_dir / f"{task_dir.name}.zh.srt"
        bilingual = task_dir / f"{task_dir.name}.bilingual.srt"
        if srt.exists() and zh.exists() and not bilingual.exists():
            try:
                create_bilingual_srt(str(srt), str(zh), str(bilingual))
                fixed += 1
            except Exception:
                pass
        total += 1
    return fixed, total


# ─────────────────────────── Summary & Main ──────────────────────────────────


def print_final_summary(output_dir: Path) -> tuple[int, int]:
    """Print a summary of completed tasks."""
    all_dirs = [d for d in sorted(output_dir.iterdir()) if d.is_dir()]
    complete = 0
    total = len(all_dirs)
    for task_dir in all_dirs:
        srt = task_dir / f"{task_dir.name}.srt"
        zh = task_dir / f"{task_dir.name}.zh.srt"
        bilingual = task_dir / f"{task_dir.name}.bilingual.srt"
        notes = task_dir / "studynotes.md"
        if srt.exists() and zh.exists() and bilingual.exists() and notes.exists():
            complete += 1
    print(f"\n{'=' * 50}")
    print(f"  Recover Summary")
    print(f"{'=' * 50}")
    print(f"  Total tasks:  {total}")
    print(f"  Complete:     {complete}")
    print(f"  Incomplete:   {total - complete}")
    print(f"{'=' * 50}\n")
    return complete, total


def main() -> None:
    """CLI entry-point."""
    import sys

    output_dir = OUTPUT_DIR

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
    else:
        print("Usage: python -m recover [scan|fix|summary]")
        return

    if cmd == "scan":
        gaps = scan_gaps(output_dir)
        total = sum(len(v) for v in gaps.values())
        print(f"\n  Found {total} gaps:")
        for k, v in sorted(gaps.items()):
            if v:
                print(f"    {k:20s}: {len(v)} dir(s)")
        return

    if cmd == "fix":
        gaps = scan_gaps(output_dir)
        local_gaps = []
        for key in ["D_monolithic", "B_transcript", "C_naming", "A_bilingual"]:
            local_gaps.extend(gaps.get(key, []))
        fixed_transcripts, _ = recover_transcripts(
            gaps.get("B_transcript", [])
        )
        fixed_monolithic, _ = recover_monolithic(
            gaps.get("D_monolithic", [])
        )
        fixed_naming, _ = recover_seminar_naming(gaps.get("C_naming", []))
        fixed_bilingual, total_bilingual = recover_bilingual(
            output_dir, gaps.get("A_bilingual", [])
        )
        print(f"\n  Fixed: {fixed_transcripts + fixed_monolithic + fixed_naming + fixed_bilingual}")
        has_api_gaps = any(
            gaps.get(k, []) for k in ["needs_translation", "needs_asr", "needs_notes"]
        )
        if has_api_gaps:
            print(f"  Remaining API gaps: needs_translation={len(gaps.get('needs_translation',[]))}, needs_asr={len(gaps.get('needs_asr',[]))}, needs_notes={len(gaps.get('needs_notes',[]))}")
        return

    if cmd == "summary":
        print_final_summary(output_dir)
        return


if __name__ == "__main__":
    main()
