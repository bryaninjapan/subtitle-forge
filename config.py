"""Global configuration for Subtitle Forge."""

import yaml  # type: ignore
from pathlib import Path
from functools import lru_cache
from typing import Any

# --- Project Paths ---
BASE_DIR = Path(__file__).parent.absolute()
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
GLOSSARY_PATH = BASE_DIR / "glossary.json"

# --- Load YAML Settings ---
SETTINGS_PATH = BASE_DIR / "settings.yaml"

def load_settings():
    if not SETTINGS_PATH.exists(): return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

_cfg: dict[str, Any] = load_settings()

# Default values if not in YAML
api_c: dict[str, Any] = _cfg.get("api", {})
DEFAULT_GEMINI_MODEL = api_c.get("model", "gemini-2.5-flash")
LITE_MODEL = api_c.get("lite_model", "gemini-2.5-flash")
PRO_MODEL = api_c.get("pro_model", "gemini-2.5-flash")

or_c: dict[str, Any] = _cfg.get("openrouter", {})
OPENROUTER_TEXT_MODEL = or_c.get("text_model", "qwen/qwen-2.5-72b-instruct:free")

pipe_c: dict[str, Any] = _cfg.get("pipeline", {})
ASR_MAX_CONCURRENT = pipe_c.get("asr_concurrent", 2)
POST_PROC_MAX_CONCURRENT = pipe_c.get("post_proc_concurrent", 4)
TRANSLATION_MAX_CONCURRENT = POST_PROC_MAX_CONCURRENT # Aliasing for compatibility
TRANSLATION_BATCH_SIZE = pipe_c.get("translation_batch_size", 50)
ENABLE_QA_LOOP = pipe_c.get("use_qa_loop", False)
ENABLE_QA_SCORING = pipe_c.get("use_qa_scoring", False)
TRANSLATION_USE_CACHING = pipe_c.get("use_context_caching", False)
MAX_COST_USD = pipe_c.get("max_cost_usd", 5.0)

costs_c: dict[str, Any] = _cfg.get("costs", {})
COST_INPUT_FLASH, COST_OUTPUT_FLASH = costs_c.get("flash", [0.10, 0.40])
COST_INPUT_LITE, COST_OUTPUT_LITE = costs_c.get("lite", [0.04, 0.16])

# --- Media Settings ---
AUDIO_SAMPLE_RATE = 16000
SILENCE_THRESHOLD = -50
MAX_FRAMES_PER_VIDEO = 20  # Limit to 20 frames per video to keep Gemini costs low
FFMPEG_BIN = "ffmpeg"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}

# --- Subtitle Prompting ---
TRANSLATION_SYSTEM_PROMPT = """\
You are a professional CFA subtitle translator. Translate the given subtitle lines from English to Simplified Chinese.

Glossary (you MUST use these translations for these terms):
{glossary_text}

Strict output rules:
- Output ONLY a valid JSON array. Nothing else.
- Format: [{{"index": <original_index>, "text": "<chinese_translation>"}}, ...]
- Every input line MUST have a corresponding output entry with the same index.
- Translate ALL text to Chinese. Do NOT output English.
- Preserve technical acronyms like NPV, IRR, LOS, CFA as-is within the Chinese text.
- Do NOT add explanations or preambles.
"""

STYLE_TEMPLATES = {
    "academic": "Tone: Academic and formal. Use precise financial terminology.",
    "casual": "Tone: Natural and conversational. Smooth phrasing for general learners.",
    "exam-focused": "Tone: Exam-oriented. Highlight key LOS terms using 【重點】 markers where appropriate."
}

# --- Glossary Logic ---
@lru_cache(maxsize=1)
def load_glossary() -> dict:
    if not GLOSSARY_PATH.exists(): return {}
    try:
        data: dict[str, Any] = yaml.safe_load(GLOSSARY_PATH.read_text(encoding="utf-8")) or {}  # type: ignore
        # Support both old string values and new dict values with hit count
        # data format: {"term": "translation"} or {"term": {"val": "trans", "hits": 10}}
        result = {}
        for k, v in data.items():  # type: ignore
            if isinstance(v, dict): result[k] = v.get("val", "")
            else: result[k] = v
        return result
    except Exception:  # type: ignore
        print("  [WARN] Failed to load glossary, returning empty.")
        return {}

def get_truncated_glossary(max_terms: int = 50) -> dict:
    full = load_glossary()
    from itertools import islice
    return dict(islice(full.items(), max_terms))

MIME_TYPES = {
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"
}
