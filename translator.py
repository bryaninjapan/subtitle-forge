"""Translation engine using OpenRouter API for subtitle translation.

Batches are sent concurrently using a ThreadPoolExecutor for maximum speed.
"""

from __future__ import annotations

import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any
from glossary_manager import update_glossary_auto  # type: ignore
from usage_tracker import log_usage  # type: ignore
from openrouter_client import get_openrouter_client  # type: ignore

from config import (
    OPENROUTER_TEXT_MODEL,
    load_glossary,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_MAX_CONCURRENT,
    TRANSLATION_SYSTEM_PROMPT,
    STYLE_TEMPLATES,
    ENABLE_QA_SCORING,
)  # type: ignore
from srt_utils import (
    SrtEntry,
    batch_entries,
    parse_srt,
    split_monolithic_entry,
    write_srt,
)  # type: ignore
from srt_translation import format_batch_for_translation, parse_translation_response

# Entries longer than this are almost certainly corrupted ASR output (entire transcript
# dumped into one subtitle block).  We split them rather than sending to the API.
_MAX_ENTRY_CHARS = 2_000

from dataclasses import dataclass

@dataclass
class UsageData:
    prompt_token_count: int
    candidates_token_count: int


def _translate_batch(
    client: Any,
    model: str,
    batch: list[SrtEntry],
    batch_index: int,
    total_batches: int,
    retries: int = 3,
    retry_delay: float = 10.0,
    glossary: dict | None = None,
    style: str = "academic",
    context: list[SrtEntry] | None = None,
) -> tuple[str, UsageData]:
    """Send a single batch of subtitle lines to OpenRouter. Thread-safe."""
    from usage_tracker import check_backoff, signal_backoff, log_failure  # type: ignore

    batch_text = format_batch_for_translation(batch, context=context)

    current_glossary = glossary or {}
    combined_text = (batch_text + " ".join(e.text for e in (context or []))).lower()
    filtered_glossary = {k: v for k, v in current_glossary.items() if k.lower() in combined_text}

    glossary_text = "\n".join(f"- {k} -> {v}" for k, v in filtered_glossary.items())
    system_instruction = TRANSLATION_SYSTEM_PROMPT.format(glossary_text=glossary_text)

    style_desc = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["academic"])
    system_instruction += f"\n\nTone guideline: {style_desc}"

    dynamic_max_tokens = min(8192, max(2048, len(batch) * 300))

    for attempt in range(1, retries + 1):
        try:
            check_backoff()

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": batch_text},
                ],
                temperature=0.1,
                max_tokens=dynamic_max_tokens,
            )

            response_text = ""
            if response and response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content or ""
            
            base_usage = UsageData(
                prompt_token_count=response.usage.prompt_tokens if response and response.usage else 0,
                candidates_token_count=response.usage.completion_tokens if response and response.usage else 0,
            )

            # QA Loop — best-effort; fall back to base translation on any failure
            from config import ENABLE_QA_LOOP  # type: ignore
            if not ENABLE_QA_LOOP or not response_text:
                return response_text, base_usage

            try:
                qa_instr = (
                    f"You are a CFA quality editor. Ensure terms in "
                    f"{list(filtered_glossary.keys())} are correct. "
                    f"Output JSON array with same format."
                )
                qa_res = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": qa_instr},
                        {"role": "user", "content": response_text},
                    ],
                    temperature=0.0,
                    max_tokens=dynamic_max_tokens,
                )
                
                qa_text = response_text
                if qa_res and qa_res.choices and len(qa_res.choices) > 0:
                    qa_text = qa_res.choices[0].message.content or response_text
                
                qa_in = qa_res.usage.prompt_tokens if qa_res and qa_res.usage else 0
                qa_out = qa_res.usage.completion_tokens if qa_res and qa_res.usage else 0
                combined_usage = UsageData(
                    prompt_token_count=base_usage.prompt_token_count + qa_in,
                    candidates_token_count=base_usage.candidates_token_count + qa_out,
                )
                return qa_text, combined_usage

            except Exception as qa_err:
                print(f"  [QA] Failed (using base translation): {qa_err}")
                return response_text, base_usage

        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["429", "quota", "overloaded", "503", "rate limit"]):
                wait = (retry_delay * (2 ** (attempt - 1))) + random.uniform(0, 1)
                signal_backoff(wait + 2)
                time.sleep(wait)
            elif attempt == retries:
                log_failure("Translation", f"Batch {batch_index}", str(e))
                raise
            else:
                time.sleep(retry_delay)

    raise RuntimeError(f"Translation failed for batch {batch_index} after {retries} attempts.")


def translate_srt_files(
    srt_mapping: dict[Path, Path],
    model: str | None = None,
    style: str = "academic",
    dry_run: bool = False,
    series_context: str | None = None,
) -> dict[Path, Path]:
    or_model = str(model or os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL))

    print(f"\n{'='*60}")
    print(f"Translation backend: OpenRouter ({or_model}) {'[DRY RUN]' if dry_run else ''}")
    print(f"{'='*60}")

    if dry_run:
        for m_path in srt_mapping:
            print(f"  [dry-run] Would translate {m_path.name}")
        return {m: s.parent / f"{m.stem}.zh.srt" for m, s in srt_mapping.items()}

    client = get_openrouter_client()
    results: dict[Path, Path] = {}
    current_glossary = load_glossary()

    for i, (media_path, srt_path) in enumerate(srt_mapping.items(), 1):
        zh_srt_path = srt_path.parent / f"{media_path.stem}.zh.srt"
        if zh_srt_path.exists():
            print(f"[{i}/{len(srt_mapping)}] [skip] zh.srt already exists: {zh_srt_path.name}")
            results[media_path] = zh_srt_path
            continue

        # Pre-flight: validate the SRT before calling any API
        entries = []
        try:
            entries = parse_srt(srt_path.read_text(encoding="utf-8"))
        except Exception as e:
            from usage_tracker import log_failure  # type: ignore
            log_failure("Translation", media_path.name, f"Cannot read SRT: {e}")
            print(f"[{i}/{len(srt_mapping)}] [ERROR] Cannot read SRT: {e}")
            continue
        if not entries:
            from usage_tracker import log_failure  # type: ignore
            log_failure("Translation", media_path.name, "SRT has 0 entries")
            print(f"[{i}/{len(srt_mapping)}] [WARN] SRT has 0 entries, skipping.")
            continue

        # Guard: split any oversized entries before batching (catches garbled ASR output
        # where the entire transcript was collapsed into a single subtitle block).
        oversized = [e for e in entries if len(e.text) > _MAX_ENTRY_CHARS]
        if oversized:
            repaired: list[SrtEntry] = []
            for e in entries:
                if len(e.text) > _MAX_ENTRY_CHARS:
                    repaired.extend(split_monolithic_entry(e))
                else:
                    repaired.append(e)
            for idx, e in enumerate(repaired, 1):
                e.index = idx
            entries = repaired
            print(f"  [REPAIR] Split {len(oversized)} oversized entries → {len(entries)} total")

        print(f"[{i}/{len(srt_mapping)}] Translating {len(entries)} subtitles -> {zh_srt_path.name}")

        try:
            update_glossary_auto(srt_path)
            current_glossary = load_glossary()

            batches = batch_entries(entries, TRANSLATION_BATCH_SIZE)
            cache_dir = zh_srt_path.parent / "translation_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            ordered_futures: list[Any] = []
            total_in = 0
            total_out = 0
            translated_entries: list[Any] = []

            with ThreadPoolExecutor(max_workers=TRANSLATION_MAX_CONCURRENT) as executor:
                for bi, batch in enumerate(batches):
                    # Batch cache with validation
                    cache_file = cache_dir / f"batch_{bi}.json"
                    if cache_file.exists():
                        try:
                            cached_text = cache_file.read_text(encoding="utf-8")
                            test = parse_translation_response(cached_text, batch)
                            if any(test):
                                from concurrent.futures import Future
                                f: Any = Future()
                                f.set_result((cached_text, None))
                                ordered_futures.append((bi, batch, f))
                                continue
                            else:
                                print(f"  [Cache] batch_{bi} stale/invalid, re-translating.")
                                cache_file.unlink()
                        except Exception:
                            cache_file.unlink()

                    context_entries: list[Any] = batches[bi - 1][-3:] if bi > 0 else []  # type: ignore[index]
                    if bi == 0 and series_context:
                        context_entries.insert(0, SrtEntry(0, "00:00:00,000", "00:00:00,000", f"[SERIES CONTEXT]: {series_context}"))

                    ordered_futures.append((bi, batch, executor.submit(  # type: ignore[arg-type]
                        _translate_batch, client, or_model, batch, bi, len(batches),
                        glossary=current_glossary, style=style, context=context_entries,
                    )))

                for bi, batch, future in ordered_futures:
                    raw_res, usage = future.result()
                    (cache_dir / f"batch_{bi}.json").write_text(raw_res, encoding="utf-8")
                    translations = parse_translation_response(raw_res, batch)
                    if usage:
                        total_in = total_in + int(getattr(usage, "prompt_token_count", 0))  # type: ignore[operator]
                        total_out = total_out + int(getattr(usage, "candidates_token_count", 0))  # type: ignore[operator]
                    translated_entries.extend([
                        SrtEntry(e.index, e.start, e.end, p_text)
                        for e, p_text in zip(batch, translations)
                    ])

            # Validate: output must be Chinese
            def _is_chinese(text: str) -> bool:
                chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                return len(text) > 0 and chinese_chars > len(text) * 0.1

            sample: list[str] = [e.text for e in list(translated_entries)[:10]]  # type: ignore[attr-defined]
            chinese_count = sum(1 for t in sample if _is_chinese(t))
            if chinese_count < max(1, len(sample) // 2):
                from usage_tracker import log_failure  # type: ignore
                log_failure("Translation", media_path.name, f"Only {chinese_count}/{len(sample)} entries are Chinese. Sample: {sample[:2]}")
                print(f"  [ERROR] Translation incomplete ({chinese_count}/{len(sample)} Chinese). Purging cache.")
                for cf in cache_dir.glob("batch_*.json"):
                    cf.unlink(missing_ok=True)
                continue

            write_srt(translated_entries, zh_srt_path)
            log_usage("Translation", media_path.name, total_in, total_out, model=or_model)
            print(f"  Saved: {zh_srt_path.name}")
            results[media_path] = zh_srt_path

        except Exception as e:
            from usage_tracker import log_failure  # type: ignore
            log_failure("Translation", media_path.name, str(e))
            print(f"  [ERROR] Translation failed for {media_path.name}: {e}")

    return results


def translate_one_video(raw_srt_text: str, visual_context_summary: Optional[str], style: str, working_directory: str) -> Dict[str, Any]:
    """Single-video translation wrapper for the Multi-Agent Director."""
    w_d = Path(working_directory)

    entries = parse_srt(raw_srt_text)

    client = get_openrouter_client()
    or_model = str(os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL))

    batches = batch_entries(entries, batch_size=TRANSLATION_BATCH_SIZE)

    translated_entries: list[str] = []
    total_in = 0
    total_out = 0

    current_glossary = load_glossary()

    for i, batch in enumerate(batches):
        context_entries = batches[i - 1][-3:] if i > 0 else []
        if i == 0 and visual_context_summary:
            context_entries.insert(0, SrtEntry(0, "00:00:00,000", "00:00:00,000", f"[SERIES CONTEXT]: {visual_context_summary}"))

        res_text, usage = _translate_batch(
            client, or_model, batch, i, len(batches),
            glossary=current_glossary, style=style, context=context_entries,
        )
        translated_entries.extend(parse_translation_response(res_text, batch))
        if usage:
            total_in = total_in + int(getattr(usage, "prompt_token_count", 0))  # type: ignore[operator]
            total_out = total_out + int(getattr(usage, "candidates_token_count", 0))  # type: ignore[operator]

    log_usage("Translation", w_d.name, total_in, total_out, model=or_model)

    zh_srt_p = w_d / f"{w_d.name}.zh.srt"
    final_zh = [SrtEntry(e.index, e.start, e.end, txt) for e, txt in zip(entries, translated_entries)]
    write_srt(final_zh, zh_srt_p)

    return {
        "zh_srt_text": zh_srt_p.read_text(encoding="utf-8"),
        "zh_srt_path": str(zh_srt_p),
    }
