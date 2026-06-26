"""Audio quality check — uses Gemini to analyze audio clarity."""
import os
import subprocess
from pathlib import Path

from gemini_client import get_gemini_client
from google.genai import types


def check_audio_quality(media_path: Path) -> str:
    """Use Gemini to analyze whether audio is clear enough for ASR."""
    from config import OUTPUT_DIR
    client = get_gemini_client()
    tmp_audio = OUTPUT_DIR / f"quality_check_{os.getpid()}.wav"
    subprocess.run(
        ["ffmpeg", "-i", str(media_path), "-t", "30", "-vn", "-ac", "1", "-ar", "16000", "-y", str(tmp_audio)],
        capture_output=True,
    )
    if not tmp_audio.exists():
        return "Unknown"
    try:
        up = client.files.upload(file=str(tmp_audio), config={"mime_type": "audio/wav"})
        from config import LITE_MODEL
        res = client.models.generate_content(
            model=LITE_MODEL,
            contents=[types.Part.from_uri(file_uri=up.uri, mime_type=up.mime_type)],
            config=types.GenerateContentConfig(
                system_instruction="Analyze audio quality. Is it clear? Return 'Good' or a short warning."
            ),
        )
        client.files.delete(name=up.name)
        tmp_audio.unlink()
        return res.text.strip()
    except (OSError, KeyError):
        if tmp_audio.exists():
            tmp_audio.unlink()
        return "Unknown"
