"""Translation engine using Google Gemini API for subtitle translation.

Batches are sent concurrently using a ThreadPoolExecutor for maximum speed.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from glossary_manager import update_glossary_auto
from usage_tracker import log_usage


from config import (
    DEFAULT_GEMINI_MODEL,
    load_glossary,
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
    glossary: dict | None = None,
    cached_content_name: str | None = None,
    style: str = "academic",
) -> tuple[str, object]:
    """Send a single batch of subtitle lines to Gemini. Thread-safe."""
    from google.genai import types

    system_instruction = None
    if not cached_content_name:
        # Prepare glossary text
        current_glossary = glossary or {}
        glossary_lines = [f"- {k} -> {v}" for k, v in current_glossary.items()]
        glossary_text = "\n".join(glossary_lines)
        
        system_instruction = TRANSLATION_SYSTEM_PROMPT.format(glossary_text=glossary_text)
        system_instruction += f"\nTranslation Style: {style.upper()} - Use appropriate tone and professional terminology."
        system_instruction += "\nOutput MUST be a JSON list of objects: [{\"index\": 1, \"text\": \"translation\"}, ...]"
    
    import random
    
    for attempt in range(1, retries + 1):
        try:
            from usage_tracker import check_backoff, signal_backoff
            check_backoff() # Wave 7: Wait if others hit rate limits
            
            config_params = {
                "temperature": 0.1,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json",
            }
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            if cached_content_name:
                config_params["cached_content"] = cached_content_name

            response = client.models.generate_content(
                model=model,
                contents=batch_text,
                config=types.GenerateContentConfig(**config_params),
            )
            # Stage 2: Reflective QA Loop
            qa_system_instruction = f"""
You are a CFA quality control editor. Review the JSON translation for:
1. Glossary adherence ({glossary_text})
2. Professional terminology
3. Phrasing errors

Output corrected JSON in the same format.
            """
            
            qa_response = client.models.generate_content(
                model=model,
                contents=response.text,
                config=types.GenerateContentConfig(
                    system_instruction=qa_system_instruction,
                    temperature=0.0, # Strict check
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )
            
            # Combine usage
            total_usage = response.usage_metadata
            if qa_response.usage_metadata:
                total_usage.prompt_token_count += qa_response.usage_metadata.prompt_token_count
                total_usage.candidates_token_count += qa_response.usage_metadata.candidates_token_count
                total_usage.total_token_count += qa_response.usage_metadata.total_token_count
                
            return qa_response.text, total_usage

        except Exception as e:
            err_str = str(e).lower()
            # Exponential Backoff with Jitter: base * 2^attempt + random_jitter
            # Target 429 Too Many Requests / Overloaded
            is_rate_limit = any(x in err_str for x in ["429", "quota", "resource_exhausted", "limit"])
            is_overloaded = "503" in err_str or "overloaded" in err_str
            
            if is_rate_limit or is_overloaded:
                base_delay = retry_delay if is_rate_limit else 2.0
                jitter = random.uniform(0, 1)
                wait = (base_delay * (2 ** (attempt - 1))) + jitter
                
                # Wave 7: Signal global backoff
                signal_backoff(wait + 2)
            else:
                wait = retry_delay

            if attempt < retries:
                print(f"  [retry {attempt}/{retries}] Batch {batch_index}/{total_batches}: {e} — retrying in {wait:.1f}s")
                time.sleep(wait)
            else:
                from usage_tracker import log_failure
                log_failure("Translation", f"Batch {batch_index}", str(e))
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
    gemini_model = model or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    print(f"\n{'='*60}")
    print(f"Translation backend: Google Gemini API ({gemini_model})")
    print(f"Concurrent batches: {TRANSLATION_MAX_CONCURRENT}")
    print(f"{'='*60}")

    client = _get_gemini_client()
    print("Gemini client initialized.\n")

    results: dict[Path, Path] = {}
    
    # Reload glossary once at the start
    current_glossary = load_glossary()
    
    # Wave 6: Context Caching Logic
    from config import TRANSLATION_USE_CACHING
    cached_content_name = None
    if TRANSLATION_USE_CACHING and len(current_glossary) > 50:
        print(f"  [Cache] Large glossary detected ({len(current_glossary)} terms). Creating context cache...")
        try:
            from google.genai import types
            glossary_lines = [f"- {k} -> {v}" for k, v in current_glossary.items()]
            glossary_text = "\n".join(glossary_lines)
            cache_instruction = TRANSLATION_SYSTEM_PROMPT.format(glossary_text=glossary_text)
            
            # Create a 1-hour cache for this session
            cache = client.caches.create(
                model=gemini_model,
                config=types.CreateCachedContentConfig(
                    system_instruction=cache_instruction,
                    ttl="3600s",
                ),
            )
            cached_content_name = cache.name
            print(f"  [Cache] Created: {cached_content_name}")
        except Exception as e:
            print(f"  [Cache] Failed to create cache: {e}. Falling back to standard requests.")

    for i, (media_path, srt_path) in enumerate(srt_mapping.items(), 1):
        zh_srt_path = srt_path.parent / f"{media_path.stem}.zh.srt"
        
        # --- PHASE 3: Task Recovery (Checkpointing) ---
        if zh_srt_path.exists():
            print(f"[{i}/{len(srt_mapping)}] [skip] Chinese translation already exists: {zh_srt_path.name}")
            results[media_path] = zh_srt_path
            continue

        print(f"[{i}/{len(srt_mapping)}] Translating: {srt_path.name}")
        
        # --- PHASE 2: AI Auto-Learning Mode ---
        # Scan the transcript and update the glossary JSON automatically
        # Note: If catching is used, auto-learning won't update the cache mid-run.
        try:
            update_glossary_auto(srt_path)
            if not cached_content_name: # Only reload if not using a fixed cache
                current_glossary = load_glossary()
        except Exception as e:
            print(f"  [Glossary] Auto-update skipped: {e}")

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
                    # For context, we take the last 3 lines of the previous batch
                    context = batches[bi-2][-3:] if bi > 1 else None
                    
                    batch_text = format_batch_for_translation(batch, context=context)
                    future = executor.submit(
                        _translate_batch_gemini,
                        client,
                        gemini_model,
                        batch_text,
                        bi,
                        total,
                        glossary=current_glossary if not cached_content_name else None,
                        style=os.environ.get("TRANSLATION_STYLE", "academic")
                    )
                    ordered_futures.append((bi, batch, future))

                # Collect results
                translated_entries: list[SrtEntry] = []
                total_usage = {"input": 0, "output": 0, "total": 0}
                
                for bi, batch, future in ordered_futures:
                    raw_result, usage = future.result()
                    translations = parse_translation_response(raw_result, batch)
                    
                    if usage:
                        total_usage["input"] += usage.prompt_token_count
                        total_usage["output"] += usage.candidates_token_count
                        total_usage["total"] += usage.total_token_count

                    translated_entries.extend([
                        SrtEntry(e.index, e.start, e.end, p_text)
                        for e, p_text in zip(batch, translations)
                    ])

            zh_srt_path = srt_path.parent / f"{media_path.stem}.zh.srt"
            write_srt(translated_entries, zh_srt_path)
            results[media_path] = zh_srt_path
            
            elapsed = time.time() - t0
            print(f"  Saved: {zh_srt_path.name} (total: {elapsed:.1f}s for {len(entries)} entries)")
            if total_usage["total"] > 0:
                log_usage("Translation", media_path.name, total_usage["input"], total_usage["output"])
                print(f"  Token Usage (Translation): Input={total_usage['input']}, Output={total_usage['output']}, Total={total_usage['total']}")

        except Exception as e:
            print(f"  [ERROR] Translation failed for '{srt_path.name}': {e}")
            continue

    return results
