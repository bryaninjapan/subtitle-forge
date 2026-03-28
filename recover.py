#!/usr/bin/env python3
"""
recover.py — Universal detect-and-fix engine for incomplete pipeline outputs.
Zero API calls. Scans all output dirs, classifies gaps into a task grid,
fixes everything local-fixable, then reports what still needs the API.

Gap types:
  B) transcript.txt contains raw SRT but .srt is missing  → local fix
  C) subtitle.srt exists (old naming) but {stem}.srt is missing → local fix
  A) .srt + .zh.srt exist but .bilingual.srt is missing   → local fix
  needs_translation: has .srt but no .zh.srt              → Translation API
  needs_asr:         no .srt and no usable transcript     → ASR API
  needs_notes:       complete SRT+ZH but no studynotes.md → Notes API
"""
from __future__ import annotations
import shutil
from pathlib import Path

from config import OUTPUT_DIR # type: ignore
from srt_utils import parse_srt, write_srt, create_bilingual_srt, convert_srt_to_vtt, clean_subtitle_text, split_monolithic_entry # type: ignore

# An SRT is considered "monolithic" (garbled ASR output) when the file is large
# but has very few entries — e.g. the entire 30-min transcript in one subtitle block.
_MONOLITHIC_MIN_BYTES = 50_000   # file must be at least 50 KB
_MONOLITHIC_MAX_ENTRIES = 10     # and have fewer than 10 subtitle entries


# ─────────────────────────── Gap Scanner ─────────────────────────────────────

def scan_gaps(output_dir: Path) -> dict[str, list[Path]]:
    """Scan all output subdirs and classify gaps into recoverable categories."""
    gaps: dict[str, list[Path]] = {
        "D_monolithic":       [],
        "B_transcript":       [],
        "C_naming":           [],
        "A_bilingual":        [],
        "needs_translation":  [],
        "needs_asr":          [],
        "needs_notes":        [],
    }

    for d in sorted(output_dir.iterdir()):
        if not d.is_dir():
            continue
        stem = d.name
        srt_p        = d / f"{stem}.srt"
        zh_p         = d / f"{stem}.zh.srt"
        bi_p         = d / f"{stem}.bilingual.srt"
        transcript_p = d / f"{stem}.transcript.txt"
        old_srt      = d / "subtitle.srt"
        notes_p      = d / f"{stem}.studynotes.md"

        has_srt        = srt_p.exists()
        has_zh         = zh_p.exists()
        has_bi         = bi_p.exists()
        has_notes      = notes_p.exists()
        has_transcript = transcript_p.exists()
        has_old_srt    = old_srt.exists()

        # B: transcript.txt exists (may contain raw SRT) but no .srt
        if not has_srt and has_transcript:
            raw = transcript_p.read_text(encoding="utf-8")
            if parse_srt(raw):  # Only if parseable
                gaps["B_transcript"].append(d)
                continue  # Will get srt after fix; don't double-count

        # C: old-named subtitle.srt exists but no {stem}.srt
        if not has_srt and has_old_srt:
            gaps["C_naming"].append(d)
            continue

        # Remaining checks require .srt to exist
        if not has_srt:
            gaps["needs_asr"].append(d)
            continue

        # D: monolithic SRT — large file with very few entries (garbled ASR output)
        if srt_p.stat().st_size >= _MONOLITHIC_MIN_BYTES:
            try:
                entries = parse_srt(srt_p.read_text(encoding="utf-8"))
                if 0 < len(entries) <= _MONOLITHIC_MAX_ENTRIES:
                    gaps["D_monolithic"].append(d)
                    continue  # treat as needs repair before translation
            except Exception:
                pass

        # A: has srt + zh but no bilingual
        if has_srt and has_zh and not has_bi:
            gaps["A_bilingual"].append(d)

        # needs_translation: has srt but no zh
        if has_srt and not has_zh:
            gaps["needs_translation"].append(d)

        # needs_notes: translation complete but no study notes
        if has_srt and has_zh and has_bi and not has_notes:
            gaps["needs_notes"].append(d)

    return gaps


# ─────────────────────────── Local Fixers ────────────────────────────────────

def recover_transcripts(dirs: list[Path]) -> tuple[int, list[Path]]:
    """B: Re-parse transcript.txt files containing raw SRT."""
    fixed = []
    for d in dirs:
        stem = d.name
        srt_p        = d / f"{stem}.srt"
        transcript_p = d / f"{stem}.transcript.txt"

        raw = transcript_p.read_text(encoding="utf-8")
        entries = parse_srt(raw)
        if not entries:
            print(f"  [SKIP-B] {stem}: still unparseable ({len(raw)} chars)")
            continue

        for e in entries:
            e.text = clean_subtitle_text(e.text)
        entries = [e for e in entries if e.text]
        if not entries:
            print(f"  [SKIP-B] {stem}: all entries empty after cleaning")
            continue

        write_srt(entries, srt_p)
        transcript_p.write_text(" ".join(e.text for e in entries) + "\n", encoding="utf-8")
        print(f"  [OK-B] {stem}: recovered {len(entries)} entries → {srt_p.name}")
        fixed.append(d)

    return len(fixed), fixed


def recover_monolithic(dirs: list[Path]) -> tuple[int, list[Path]]:
    """D: Split monolithic SRT files (entire transcript in ≤10 entries) into proper subtitles.

    Uses synthetic timestamps based on ~130 words/min speaking rate.
    The original corrupted file is preserved as <stem>.srt.bak before overwriting.
    """
    fixed = []
    for d in dirs:
        stem  = d.name
        srt_p = d / f"{stem}.srt"
        bak_p = d / f"{stem}.srt.bak"

        try:
            raw_entries = parse_srt(srt_p.read_text(encoding="utf-8"))
            if not raw_entries:
                print(f"  [SKIP-D] {stem}: could not parse existing SRT")
                continue

            new_entries = []
            for e in raw_entries:
                if len(e.text) > 500:
                    new_entries.extend(split_monolithic_entry(e))
                else:
                    new_entries.append(e)

            # Re-index
            for i, e in enumerate(new_entries, 1):
                e.index = i

            if len(new_entries) <= len(raw_entries):
                print(f"  [SKIP-D] {stem}: split produced no new entries (already minimal?)")
                continue

            # Back up the corrupted file, write the repaired one
            srt_p.rename(bak_p)
            write_srt(new_entries, srt_p)
            print(f"  [OK-D] {stem}: {len(raw_entries)} → {len(new_entries)} entries (bak: {bak_p.name})")
            fixed.append(d)
        except Exception as e:
            print(f"  [ERR-D] {stem}: {e}")

    return len(fixed), fixed


def recover_seminar_naming(dirs: list[Path]) -> tuple[int, list[Path]]:
    """C: Copy old-named subtitle.srt to stem-prefixed names."""
    fixed = []
    for d in dirs:
        stem    = d.name
        old_srt = d / "subtitle.srt"
        new_srt = d / f"{stem}.srt"

        shutil.copy2(old_srt, new_srt)
        print(f"  [OK-C] {stem}: copied subtitle.srt → {new_srt.name}")

        old_txt = d / "transcript.txt"
        new_txt = d / f"{stem}.transcript.txt"
        if old_txt.exists() and not new_txt.exists():
            shutil.copy2(old_txt, new_txt)

        fixed.append(d)

    return len(fixed), fixed


def recover_bilingual(output_dir: Path, target_dirs: list[Path] | None = None) -> tuple[int, int]:
    """A: Create bilingual SRT + VTT for dirs that have en+zh but no bilingual."""
    ok: int = 0
    fail: int = 0
    dirs = target_dirs if target_dirs is not None else [
        d for d in sorted(output_dir.iterdir()) if d.is_dir()
    ]

    for d in dirs:
        stem  = d.name
        en_p  = d / f"{stem}.srt"
        zh_p  = d / f"{stem}.zh.srt"
        bi_p  = d / f"{stem}.bilingual.srt"
        vtt_p = d / f"{stem}.vtt"

        if not en_p.exists() or not zh_p.exists():
            continue
        if bi_p.exists() and vtt_p.exists():
            continue

        try:
            en = parse_srt(en_p.read_text(encoding="utf-8"))
            zh = parse_srt(zh_p.read_text(encoding="utf-8"))
            if not en or not zh:
                print(f"  [WARN-A] {stem}: empty entries (en={len(en)}, zh={len(zh)})")
                fail += 1 # type: ignore
                continue

            if not bi_p.exists():
                create_bilingual_srt(en, zh, bi_p)
            if not vtt_p.exists():
                convert_srt_to_vtt(zh_p, vtt_p)

            print(f"  [OK-A] {stem}: bilingual({len(en)}e/{len(zh)}z) + vtt")
            ok += 1 # type: ignore
        except Exception as e:
            print(f"  [ERR-A] {stem}: {e}")
            fail += 1 # type: ignore

    return ok, fail


# ─────────────────────────── Summary Printer ─────────────────────────────────

def print_final_summary(output_dir: Path) -> tuple[int, int]:
    total: int = 0
    ok: int = 0
    for d in sorted(output_dir.iterdir()):
        if not d.is_dir():
            continue
        stem = d.name
        total += 1 # type: ignore
        if (
            (d / f"{stem}.srt").exists()
            and (d / f"{stem}.zh.srt").exists()
            and (d / f"{stem}.bilingual.srt").exists()
        ):
            ok += 1 # type: ignore
    print(f"\n  {ok}/{total} fully complete (srt+zh+bilingual)")
    return ok, total


# ─────────────────────────── Main ────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Subtitle Forge — Auto Detect & Fix")
    print("=" * 60)

    if not OUTPUT_DIR.exists() or not any(OUTPUT_DIR.iterdir()):
        print("\n  [INFO] Output directory is empty — nothing to fix.")
        return

    # ── Phase 1: Scan ────────────────────────────────────────────────────────
    print("\n[Scan] Analysing output directories...")
    gaps = scan_gaps(OUTPUT_DIR)

    local_fixable = gaps["D_monolithic"] + gaps["B_transcript"] + gaps["C_naming"] + gaps["A_bilingual"]
    needs_api     = gaps["needs_translation"] + gaps["needs_asr"] + gaps["needs_notes"]

    print("\n  Task Grid:")
    print("  Local-fixable (zero API cost):")
    print(f"    D  monolithic SRT split        : {len(gaps['D_monolithic'])} dirs")
    print(f"    B  re-parse transcript → .srt  : {len(gaps['B_transcript'])} dirs")
    print(f"    C  seminar rename              : {len(gaps['C_naming'])} dirs")
    print(f"    A  bilingual missing           : {len(gaps['A_bilingual'])} dirs")
    print("  Needs API:")
    print(f"    Translation  (.zh.srt)         : {len(gaps['needs_translation'])} dirs")
    print(f"    ASR          (.srt)            : {len(gaps['needs_asr'])} dirs")
    print(f"    Study Notes  (.studynotes.md)  : {len(gaps['needs_notes'])} dirs")

    if not local_fixable and not needs_api:
        print("\n  [✓] Nothing to fix — all directories are complete.")
        return

    # ── Phase 2: Local fixes ─────────────────────────────────────────────────
    b_count = c_count = 0
    b_new_dirs: list[Path] = []
    c_new_dirs: list[Path] = []
    d_new_dirs: list[Path] = []

    if gaps["D_monolithic"]:
        print(f"\n[Step 0] Splitting monolithic SRTs (D class: {len(gaps['D_monolithic'])})...")
        d_count, d_new_dirs = recover_monolithic(gaps["D_monolithic"])
        print(f"  → {d_count} SRT files repaired (now eligible for translation)")

    if gaps["B_transcript"]:
        print(f"\n[Step 1] Re-parsing transcripts (B class: {len(gaps['B_transcript'])})...")
        b_count, b_new_dirs = recover_transcripts(gaps["B_transcript"])
        print(f"  → {b_count} SRT files recovered")

    if gaps["C_naming"]:
        print(f"\n[Step 2] Fixing seminar naming (C class: {len(gaps['C_naming'])})...")
        c_count, c_new_dirs = recover_seminar_naming(gaps["C_naming"])
        print(f"  → {c_count} directories renamed")

    # After B+C fixes, newly created .srt dirs may now be eligible for bilingual
    # Re-scan A_bilingual to pick them up
    bilingual_targets = gaps["A_bilingual"] + b_new_dirs + c_new_dirs + d_new_dirs

    if bilingual_targets:
        print(f"\n[Step 3] Creating bilingual SRT + VTT (A class + newly fixed)...")
        ok, fail = recover_bilingual(OUTPUT_DIR, target_dirs=bilingual_targets)
        print(f"  → {ok} created, {fail} failed")

    # ── Phase 3: API report ───────────────────────────────────────────────────
    if needs_api:
        print("\n[API Required] The following gaps need the pipeline to run:")
        if gaps["needs_asr"]:
            print(f"  ASR ({len(gaps['needs_asr'])} dirs):")
            for d in gaps["needs_asr"]:
                print(f"    {d.name}")
        if gaps["needs_translation"]:
            print(f"  Translation ({len(gaps['needs_translation'])} dirs):")
            for d in gaps["needs_translation"]:
                print(f"    {d.name}")
        if gaps["needs_notes"]:
            print(f"  Study Notes ({len(gaps['needs_notes'])} dirs):")
            for d in gaps["needs_notes"]:
                print(f"    {d.name}")
        print("\n  Suggested command:")
        print("    ./venv/bin/python3 main.py input/ --language English")
    else:
        print("\n[✓] All local-fixable gaps resolved — no API calls needed.")

    # ── Phase 4: Final summary ────────────────────────────────────────────────
    print("\n[Final Status]")
    ok, total = print_final_summary(OUTPUT_DIR)

    if ok < total:
        print("\n  [NOTE] Run `./venv/bin/python3 main.py input/ --language English` to complete remaining videos.")


if __name__ == "__main__":
    main()
