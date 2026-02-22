from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

ASR_MODEL = "Qwen/Qwen3-ASR-1.7B"
TRANSLATION_MODEL = "mlx-community/Qwen3-8B-4bit"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".ts"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}

FFMPEG_BIN = "ffmpeg"
AUDIO_SAMPLE_RATE = 16000

TRANSLATION_BATCH_SIZE = 25
TRANSLATION_MAX_TOKENS = 4096

TRANSLATION_SYSTEM_PROMPT = """\
你是專業的教學影片字幕翻譯員。請將以下字幕翻譯為繁體中文。

規則：
- 逐條翻譯，保持與原文一一對應，不增不減
- 每條翻譯獨佔一行，格式為：序號|翻譯內容
- 保持專業術語準確，不確定的術語保留原文並括號附註中文
- 譯文簡潔自然，符合字幕閱讀節奏
- 不要添加任何解釋、註釋或額外文字\
"""
