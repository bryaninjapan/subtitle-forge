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

# 金融/技術術語對照表 (Glossary)
GLOSSARY = {
    "CFA": "特許金融分析師",
    "Equity": "權益/股權",
    "Fixed Income": "固定收益",
    "Derivatives": "衍生性商品",
    "Portfolio Management": "投資組合管理",
    "Ethics": "倫理道德",
    "Economics": "經濟學",
    "Corporate Issuers": "企業發行商",
    "Alternative Investments": "另類投資",
    "Quantitative Methods": "計量方法",
    "Level 1": "第一級",
}

# 增加 ASR 並發數設定（Gemini API 支援非同步處理）
ASR_MAX_CONCURRENT = 2  # 預設同時處理 2 部影片

TRANSLATION_SYSTEM_PROMPT = """\
你是專業的教學影片字幕翻譯員。請將以下字幕翻譯為繁體中文。

規則：
- 逐條翻譯，保持與原文一一對應，不增不減
- 每條翻譯獨佔一行，格式為：序號|翻譯內容
- 保持專業術語準確，不確定的術語保留原文並括號附註中文
- 譯文簡潔自然，符合字幕閱讀節奏
- 不要添加任何解釋、註釋或額外文字

請嚴格遵守以下術語對接（原文 -> 繁體中文）：
{glossary_text}\
"""
