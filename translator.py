"""Translation engine using mlx-lm with Qwen3 for subtitle translation."""

from __future__ import annotations

import gc
import time
from pathlib import Path

from config import (
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_MAX_TOKENS,
    TRANSLATION_MODEL,
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


def _build_prompt(batch_text: str) -> list[dict[str, str]]:
    """Build chat messages for the translation model."""
    return [
        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
        {"role": "user", "content": batch_text},
    ]


def translate_srt_files(
    srt_mapping: dict[Path, Path],
) -> dict[Path, Path]:
    """Translate SRT files from original language to Chinese.

    Args:
        srt_mapping: {media_path: original_srt_path} from ASR step

    Returns:
        {media_path: chinese_srt_path} for successfully translated files.
    """
    from mlx_lm import generate, load

    print(f"\n{'='*60}")
    print(f"Loading translation model: {TRANSLATION_MODEL}")
    print(f"{'='*60}")
    t0 = time.time()
    model, tokenizer = load(TRANSLATION_MODEL)
    print(f"Model loaded in {time.time() - t0:.1f}s\n")

    results: dict[Path, Path] = {}

    for i, (media_path, srt_path) in enumerate(srt_mapping.items(), 1):
        print(f"[{i}/{len(srt_mapping)}] Translating: {srt_path.name}")

        try:
            content = srt_path.read_text(encoding="utf-8")
            entries = parse_srt(content)

            if not entries:
                print("  [skip] No subtitle entries found")
                continue

            translated_entries: list[SrtEntry] = []
            batches = batch_entries(entries, TRANSLATION_BATCH_SIZE)

            for bi, batch in enumerate(batches, 1):
                print(
                    f"  Batch {bi}/{len(batches)} "
                    f"(entries {batch[0].index}-{batch[-1].index})"
                )

                batch_text = format_batch_for_translation(batch)
                messages = _build_prompt(batch_text)
                prompt = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                    enable_thinking=False,
                )

                response = generate(
                    model, tokenizer, prompt=prompt,
                    max_tokens=TRANSLATION_MAX_TOKENS, verbose=False,
                )

                translations = parse_translation_response(response, batch)

                for entry, translated_text in zip(batch, translations):
                    translated_entries.append(SrtEntry(
                        index=entry.index,
                        start=entry.start,
                        end=entry.end,
                        text=translated_text,
                    ))

            zh_srt_path = srt_path.parent / f"{media_path.stem}.zh.srt"
            write_srt(translated_entries, zh_srt_path)
            print(f"  Saved: {zh_srt_path.name}")
            results[media_path] = zh_srt_path

        except Exception as e:
            print(f"  [ERROR] Translation failed: {e}")

    # Free translation model memory
    del model, tokenizer
    gc.collect()

    return results
