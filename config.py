from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".ts"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}

FFMPEG_BIN = "ffmpeg"
AUDIO_SAMPLE_RATE = 16000

# Gemini API Settings
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
TRANSLATION_BATCH_SIZE = 50  # Gemini API handles larger batches efficiently
TRANSLATION_MAX_CONCURRENT = 5  # Max concurrent API calls for translation batches
TRANSLATION_MAX_TOKENS = 4096

# Vision / Multimodal Settings
MAX_FRAMES_PER_VIDEO = 50  # Limit number of keyframes sent to Gemini to avoid 400 errors/token limits

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

# ASR 並發數設定
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
# MIME Types mapping
MIME_TYPES = {
    # Video
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".flv": "video/flv",
    ".m4v": "video/mp4",
    ".ts": "video/mp2t",
    # Audio
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".aac": "audio/aac",
}
