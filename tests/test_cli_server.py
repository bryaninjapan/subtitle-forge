"""Characterization smoke tests for main.py and server.py — UX-1 safety net."""
import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


# ── main.py argument parsing ─────────────────────────────────────────────

def test_main_parser_basic():
    """main() parser recognises all existing flags without error."""
    from main import build_parser

    parser = build_parser()
    # All current flags should be accepted
    args = parser.parse_args([])
    assert args.server is False
    assert args.watch is False
    assert args.wipe is False
    assert args.dry_run is False
    assert args.chapters is True


def test_main_parser_server_flag():
    """--server flag sets server=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--server"])
    assert args.server is True


def test_main_parser_watch_flag():
    """--watch flag sets watch=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--watch"])
    assert args.watch is True


def test_main_parser_wipe_flag():
    """--wipe flag sets wipe=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--wipe"])
    assert args.wipe is True


def test_main_parser_dry_run():
    """--dry-run flag sets dry_run=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True


def test_main_parser_no_chapters():
    """--no-chapters sets chapters=False."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--no-chapters"])
    assert args.chapters is False


def test_main_parser_language():
    """--language / -l sets language."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--language", "zh"])
    assert args.language == "zh"
    args = parser.parse_args(["-l", "en"])
    assert args.language == "en"


def test_main_parser_style():
    """--style sets style."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--style", "exam-focused"])
    assert args.style == "exam-focused"


def test_main_parser_paths():
    """Positional paths argument works."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["video.mp4", "dir/"])
    assert len(args.paths) == 2
    assert str(args.paths[0]) == "video.mp4"


def test_main_parser_interactive():
    """--interactive / -i flag sets interactive=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--interactive"])
    assert args.interactive is True
    args = parser.parse_args(["-i"])
    assert args.interactive is True


def test_main_parser_completion():
    """--completion accepts zsh or bash."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--completion", "zsh"])
    assert args.completion == "zsh"
    args = parser.parse_args(["--completion", "bash"])
    assert args.completion == "bash"


def test_generate_completion_zsh_output():
    """generate_completion('zsh') prints a valid zsh completion function."""
    from main import generate_completion

    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        generate_completion("zsh")
    finally:
        sys.stdout = old
    output = buf.getvalue()
    assert "#compdef" in output
    assert "_subtitle_forge" in output
    assert "--language" in output
    assert "--style" in output
    assert "academic" in output or "casual" in output


def test_generate_completion_bash_output():
    """generate_completion('bash') prints a valid bash completion function."""
    from main import generate_completion

    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        generate_completion("bash")
    finally:
        sys.stdout = old
    output = buf.getvalue()
    assert "COMPREPLY" in output
    assert "_subtitle_forge_completion" in output
    assert "--language" in output
    assert "complete -F" in output


def test_main_parser_no_notify():
    """--no-notify flag sets no_notify=True."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--no-notify"])
    assert args.no_notify is True


def test_main_parser_burn():
    """--burn and --burn-font-size flags parse correctly."""
    from main import build_parser

    parser = build_parser()
    args = parser.parse_args(["--burn"])
    assert args.burn is True
    assert args.burn_font_size == 24

    args = parser.parse_args(["--burn", "--burn-font-size", "36"])
    assert args.burn is True
    assert args.burn_font_size == 36


def test_send_notification_does_not_crash():
    """send_notification is non-blocking and does not raise."""
    from main import send_notification

    # Should not raise regardless of environment
    send_notification("Test", "This is a test notification")


def test_check_silence_fallback_on_empty_audio():
    """check_silence handles non-existent audio gracefully (no crash)."""
    from asr_engine import check_silence
    from pathlib import Path

    # Non-existent file should not crash (handled by try/except)
    result = check_silence(Path("/tmp/nonexistent_audio.wav"))
    assert result in (True, False)  # Should return a boolean


# ── srt_burn.py tests ───────────────────────────────────────────────────


def test_find_best_subtitle_prioritizes_bilingual():
    """find_best_subtitle returns bilingual.srt when available."""
    from srt_burn import find_best_subtitle
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "video.bilingual.srt").write_text("test", encoding="utf-8")
        (d / "video.srt").write_text("test", encoding="utf-8")

        result = find_best_subtitle("video.mp4", [d])
        assert result is not None
        assert "bilingual" in result.name


def test_find_best_subtitle_fallback_to_srt():
    """find_best_subtitle falls back to .srt when bilingual not available."""
    from srt_burn import find_best_subtitle
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "video.srt").write_text("test", encoding="utf-8")

        result = find_best_subtitle("video.mp4", [d])
        assert result is not None
        assert result.suffix == ".srt"


def test_find_best_subtitle_returns_none():
    """find_best_subtitle returns None when no subtitle found."""
    from srt_burn import find_best_subtitle
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        result = find_best_subtitle("nonexistent.mp4", [d])
        assert result is None


def test_burn_subtitles_no_crash_on_bad_input():
    """burn_subtitles returns False gracefully on non-existent files."""
    from srt_burn import burn_subtitles
    from pathlib import Path

    result = burn_subtitles(
        Path("/tmp/nonexistent_video.mp4"),
        Path("/tmp/nonexistent.srt"),
        Path("/tmp/output.mp4"),
    )
    assert result is False


# ── asr_api.py tests ────────────────────────────────────────────────────


def test_seconds_to_srt_time():
    """_seconds_to_srt_time converts correctly."""
    from asr_api import _seconds_to_srt_time
    assert _seconds_to_srt_time(0) == "00:00:00,000"
    assert _seconds_to_srt_time(90.5) == "00:01:30,500"
    assert _seconds_to_srt_time(3661) == "01:01:01,000"


def test_group_segments_into_srt():
    """_group_segments_into_srt produces valid SRT blocks."""
    from asr_api import _group_segments_into_srt

    segments = [
        {"text": "Hello", "start": 0.0, "end": 0.5},
        {"text": "world.", "start": 0.5, "end": 1.0},
        {"text": "Test", "start": 2.0, "end": 2.5},
    ]
    srt = _group_segments_into_srt(segments)
    assert "00:00:00,000" in srt
    assert "Hello" in srt
    assert "Test" in srt
    assert "-->" in srt


def test_transcribe_via_api_no_key_raises():
    """transcribe_via_api raises RuntimeError when API key is not set."""
    from asr_api import transcribe_via_api
    from pathlib import Path
    import os

    # Temporarily unset the key
    key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        import pytest
        with pytest.raises(RuntimeError, match="API key"):
            transcribe_via_api(Path("/tmp/test.wav"))
    finally:
        if key:
            os.environ["OPENROUTER_API_KEY"] = key


def test_extract_segments_empty_fallback():
    """_extract_segments_from_response handles empty/malformed responses."""
    from asr_api import _extract_segments_from_response

    # Mock response with just text (no words, no segments)
    class MockResponse:
        text = ""
        words = []
        segments = []

    result = _extract_segments_from_response(MockResponse())
    assert result == []


def test_asr_backend_switch_wired():
    """_transcribe_with_qwen3_asr has API/local backend switch."""
    from asr_engine import _transcribe_with_qwen3_asr
    import inspect

    src = inspect.getsource(_transcribe_with_qwen3_asr)
    assert 'ASR_BACKEND == "api"' in src
    assert "transcribe_via_api" in src
    assert "ASR_API_MODEL" in src


# ── server.py routes ─────────────────────────────────────────────────────


def test_server_index_returns_200():
    """GET / returns 200 with HTML content."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Subtitle Forge" in html


def test_server_index_has_htmx():
    """Index page includes HTMX and dashboard sections."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/")
        html = resp.data.decode("utf-8")
        assert "htmx.org" in html
        assert "drop-zone" in html
        assert "Active Tasks" in html or "active tasks" in html
        assert "History" in html


def test_server_progress_returns_json():
    """GET /progress returns JSON with task progress."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/progress")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)


def test_server_history_returns_json():
    """GET /history returns JSON array."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


def test_server_outputs_returns_json():
    """GET /outputs returns JSON array."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/outputs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


def test_server_progress_html_returns_html():
    """GET /progress-html returns HTML snippet."""
    from server import app

    with app.test_client() as client:
        resp = client.get("/progress-html")
        assert resp.status_code == 200
        content_type = resp.content_type or ""
        assert "text/html" in content_type or resp.data


def test_server_upload_no_file_returns_400():
    """POST /upload without file returns 400."""
    from server import app

    with app.test_client() as client:
        resp = client.post("/upload", data={})
        assert resp.status_code == 400
        assert resp.get_json().get("error")


def test_server_upload_bad_extension_returns_400():
    """POST /upload with disallowed extension returns 400."""
    from server import app

    with app.test_client() as client:
        resp = client.post("/upload", data={"file": (b"fake", "test.pdf")})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        assert "error" in data
