import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

ASR_MODEL_REPO = "Qwen/Qwen3-ASR-1.7B"


def _get_asr_model_path() -> str:
    """Prefer local path to avoid Hugging Face Hub check on every run."""
    # 1. Explicit local path from env
    env_path = os.environ.get("SUBTITLE_FORGE_ASR_MODEL", "").strip()
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists() and (p / "config.json").exists():
            return str(p)
    # 2. Use Hugging Face cache if model already downloaded
    cache_dir = Path(
        os.environ.get("HF_HOME", os.environ.get("HUGGINGFACE_HUB_CACHE", ""))
        or os.path.expanduser("~/.cache/huggingface/hub")
    )
    repo_cache = cache_dir / f"models--{ASR_MODEL_REPO.replace('/', '--')}" / "snapshots"
    if repo_cache.exists():
        for snap in repo_cache.iterdir():
            if snap.is_dir() and (snap / "config.json").exists():
                return str(snap.resolve())
    # 3. Fall back to repo ID (will trigger download/cache check)
    return ASR_MODEL_REPO


ASR_MODEL = _get_asr_model_path()
# 每個音訊區塊最多產生的 token 數，過小會導致長影片逐字稿被截斷（庫預設 1024）
# 超長單段可提高到 16384 或 32768，需注意顯存
ASR_MAX_NEW_TOKENS = 16384

TRANSLATION_MODEL = "mlx-community/Qwen3-8B-4bit"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".ts"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}

FFMPEG_BIN = "ffmpeg"
AUDIO_SAMPLE_RATE = 16000

TRANSLATION_BATCH_SIZE = 50  # Gemini API handles larger batches efficiently
TRANSLATION_MAX_CONCURRENT = 10  # Max concurrent API calls for translation batches
TRANSLATION_MAX_TOKENS = 4096

# 金融/技術術語對照表 (由 glossary.json 讀取)
GLOSSARY_PATH = BASE_DIR / "glossary.json"

def load_glossary() -> dict:
    import json
    if GLOSSARY_PATH.exists():
        try:
            return json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Failed to load glossary.json: {e}")
    return {}

GLOSSARY = load_glossary()

# 增加 ASR 並發數設定（Gemini API 支援非同步處理）
ASR_MAX_CONCURRENT = 2  # 預設同時處理 2 部影片

TRANSLATION_SYSTEM_PROMPT = """\
你是專業的教學影片字幕翻譯員與語義優化師。請將以下字幕翻譯為繁體中文。

規則：
- 逐條翻譯，保持序號（Index）與原文一一對應（不可合併或刪除序號）
- **語義優化 (Natural Phrasing)**：確保每一行翻譯都是一個完整的語義單位。如果原文在句中斷開，你可以適度調整譯文在相鄰序號間的分配，讓中文字幕讀起來自然流暢，符合人類閱讀習慣。
- 每條翻譯格式為：序號|翻譯內容
- 保持專業術語準確，遵守提供的術語表
- 不要添加任何解釋、註釋或額外文字

請嚴格遵守以下術語對接（原文 -> 繁體中文）：
{glossary_text}\
"""
