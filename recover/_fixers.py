"""Fixers for recover package."""
from __future__ import annotations
import shutil
from pathlib import Path
from config import OUTPUT_DIR
from srt_utils import parse_srt, write_srt, convert_srt_to_vtt, clean_subtitle_text, split_monolithic_entry
from srt_bilingual import create_bilingual_srt
_MONOLITHIC_MAX_ENTRY_CHARS = 2000

