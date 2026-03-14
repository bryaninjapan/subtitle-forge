"""Translation engine using Google Gemini API for subtitle translation.

Batches are sent concurrently using a ThreadPoolExecutor for maximum speed.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from config import (
    GLOSSARY,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_MAX_CONCURRENT,
    TRANSLATION_SYSTEM_PROMPT,
)
from srt_utils import (
    SrtEntry,
    batch_entries,
    format_batch_for_translation,
    parse_srt,
    parse_translation_response,
    write_srt,
)


def _get_gemini_client():
    """Initialize and return a Gemini client."""
    try:
        from google import genai
    except ImportError:
        raise ImportError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Export it before running: export GEMINI_API_KEY='your_key'"
        )
    return genai.Client(api_key=api_key)


def _translate_batch_gemini(
    client,
    model: str,
    batch_text: str,
    batch_index: int,
    total_batches: int,
    retries: int = 3,
    retry_delay: float = 10.0,
) -> str:
    """Send a single batch of subtitle lines to Gemini. Thread-safe."""
    from google.genai import types

    # Prepare glossary text
    glossary_lines = [f"- {k} -> {v}" for k, v in GLOSSARY.items()]
    glossary_text = "\n".join(glossary_lines)
    
    system_prompt = TRANSLATION_SYSTEM_PROMPT.format(glossary_text=glossary_text)
    prompt = f"{system_prompt}\n\n{batch_text}"

    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            return response.text, response.usage_metadata
        except Exception as e:
            err_str = str(e).lower()
            # Rate limit: wait longer before retrying
            wait = retry_delay * (2 ** (attempt - 1)) if "429" in err_str or "quota" in err_str else retry_delay
            if attempt < retries:
                print(f"  [retry {attempt}/{retries}] Batch {batch_index}/{total_batches}: {e} — retrying in {wait:.0f}s")
                time.sleep(wait)
            else:
                raise


def translate_srt_files(
    srt_mapping: dict[Path, Path],
    model: str | None = None,
) -> dict[Path, Path]:
    """Translate SRT files from original language to Chinese using Gemini API.
    
    All translation batches within each file are sent concurrently.

    Args:
        srt_mapping: {media_path: original_srt_path} from ASR step
        model: Gemini model name (default: from GEMINI_MODEL env or gemini-2.5-flash)

    Returns:
        {media_path: chinese_srt_path} for successfully translated files.
    """
    gemini_model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    print(f"\n{'='*60}")
    print(f"Translation backend: Google Gemini API ({gemini_model})")
    print(f"Concurrent batches: {TRANSLATION_MAX_CONCURRENT}")
    print(f"{'='*60}")

    client = _get_gemini_client()
    print("Gemini client initialized.\n")

    results: dict[Path, Path] = {}

    for i, (media_path, srt_path) in enumerate(srt_mapping.items(), 1):
        print(f"[{i}/{len(srt_mapping)}] Translating: {srt_path.name}")

        try:
            content = srt_path.read_text(encoding="utf-8")
            entries = parse_srt(content)

            if not entries:
                print("  [skip] No subtitle entries found")
                continue

            batches = batch_entries(entries, TRANSLATION_BATCH_SIZE)
            total = len(batches)
            print(f"  Submitting {total} batches concurrently (max {TRANSLATION_MAX_CONCURRENT} parallel)...")

            t0 = time.time()

            # Submit all batches concurrently
            ordered_futures: list[tuple[int, list[SrtEntry], object]] = []
            with ThreadPoolExecutor(max_workers=TRANSLATION_MAX_CONCURRENT) as executor:
                for bi, batch in enumerate(batches, 1):
                    batch_text = format_batch_for_translation(batch)
                    future = executor.submit(
                        _translate_batch_gemini,
                        client,
                        gemini_model,
                        batch_text,
                        bi,
                        total,
                    )
                    ordered_futures.append((bi, batch, future))

                # Collect results with a progress bar
                translated_entries: list[SrtEntry] = []
                total_usage = {"input": 0, "output": 0, "total": 0}
                
                with tqdm(total=total, desc="  Translating", unit="batch", leave=False) as pbar:
                    for bi, batch, future in ordered_futures:
                        raw_result, usage = future.result()
                        translations = parse_translation_response(raw_result, batch)
                        
                        if usage:
                            total_usage["input"] += usage.prompt_token_count
                            total_usage["output"] += usage.candidates_token_count
                            total_usage["total"] += usage.total_token_count

                        for entry, translated_text in zip(batch, translations):
                            translated_entries.append(SrtEntry(
                                index=entry.index,
                                start=entry.start,
                                end=entry.end,
                                text=translated_text,
                            ))
                        pbar.update(1)

            zh_srt_path = srt_path.parent / f"{media_path.stem}.zh.srt"
            write_srt(translated_entries, zh_srt_path)
            total_elapsed = time.time() - t0
            print(f"  Saved: {zh_srt_path.name} (total: {total_elapsed:.1f}s for {len(entries)} entries)")
            print(f"  Token Usage (Translation): Input={total_usage['input']}, Output={total_usage['output']}, Total={total_usage['total']}")
            results[media_path] = zh_srt_path

        except Exception as e:
            print(f"  [ERROR] Translation failed: {e}")

    return results
