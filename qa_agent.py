#!/usr/bin/env python3
"""
qa_agent.py — Evaluates translation quality via LLM-as-a-judge.
"""

import os
import re
from typing import Dict, Any

from openrouter_client import get_openrouter_client  # type: ignore
from config import OPENROUTER_TEXT_MODEL  # type: ignore

def score_translation(raw_srt_text: str, zh_srt_text: str) -> Dict[str, Any]:
    """Score translation quality from 0-10 and provide critique."""
    client = get_openrouter_client()
    model = os.environ.get("OPENROUTER_TEXT_MODEL", OPENROUTER_TEXT_MODEL)

    system_instruction = """
You are a professional linguistic judge specialized in Financial English to Simplified Chinese translation.
Compare the source text and translation provided.
Score the translation from 0 to 10 based on:
1. Accuracy: No meaning lost or changed.
2. Tone: Professional financial/academic tone.
3. Fluency: Natural sounding Simplified Chinese.

Format:
Score: [0-10]
Critique: [Short feedback]
"""

    prompt = f"### Source SRT:\n{raw_srt_text[:10000]}\n\n### Translated SRT:\n{zh_srt_text[:10000]}"  # type: ignore

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        text = (res.choices[0].message.content or "").strip()

        score = 0
        critique = "No critique available."

        score_match = re.search(r"Score:\s*(\d+)", text)
        if score_match:
            score = int(score_match.group(1))

        critique_match = re.search(r"Critique:\s*(.*)", text, re.DOTALL)
        if critique_match:
            critique = critique_match.group(1).strip()

        return {"qa_score": score, "qa_critique": critique}
    except Exception as e:
        raise e
