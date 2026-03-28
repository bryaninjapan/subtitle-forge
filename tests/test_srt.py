import pytest
from pathlib import Path
from srt_utils import parse_srt, SrtEntry, clean_subtitle_text

def test_parse_srt():
    content = "1\n00:00:01,000 --> 00:00:02,000\nHello World\n\n2\n00:00:03,000 --> 00:00:04,500\nTest line"
    entries = parse_srt(content)
    assert len(entries) == 2
    assert entries[0].text == "Hello World"
    assert entries[1].start == "00:00:03,000"

def test_clean_text():
    raw = "[Music] Hello (clears throat). This is a test."
    cleaned = clean_subtitle_text(raw)
    assert "Music" not in cleaned
    assert "clears throat" not in cleaned
    assert "This is a test." in cleaned

def test_vtt_format():
    from srt_utils import convert_srt_to_vtt
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        srt = Path(tmp) / "t.srt"
        vtt = Path(tmp) / "t.vtt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello", encoding="utf-8")
        convert_srt_to_vtt(srt, vtt)
        content = vtt.read_text(encoding="utf-8")
        assert "WEBVTT" in content
        assert "00:00:01.000" in content
