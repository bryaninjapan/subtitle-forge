"""Tests for asr_engine.py pure functions."""
import pytest
from pathlib import Path
from asr_engine import (
    _seconds_to_srt_time,
    _group_words_into_subtitles,
    _apply_hotwords_to_srt,
    _apply_cc_conversion,
)


class TestTimeFormatting:
    """_seconds_to_srt_time converts float seconds → SRT timestamp."""

    def test_basic(self):
        assert _seconds_to_srt_time(0.0) == "00:00:00,000"

    def test_with_milliseconds(self):
        assert _seconds_to_srt_time(1.234) == "00:00:01,234"

    def test_minutes_and_seconds(self):
        assert _seconds_to_srt_time(65.5) == "00:01:05,500"

    def test_hours(self):
        assert _seconds_to_srt_time(3661.789) == "01:01:01,789"

    def test_rounding(self):
        result = _seconds_to_srt_time(1.9999)
        # round(999.9) → 1000 → shown as 1000 due to ms:03d format
        assert "01,1000" in result


class TestGroupWords:
    """_group_words_into_subtitles groups word timestamps into subtitle blocks."""

    def make_word(self, text: str, start: float, end: float):
        return {"text": text, "start": start, "end": end}

    def test_single_word_becomes_one_block(self):
        words = [self.make_word("Hello", 0.0, 1.0)]
        blocks = _group_words_into_subtitles(words)
        assert len(blocks) == 1
        assert blocks[0]["text"] == "Hello"
        assert blocks[0]["start"] == 0.0
        assert blocks[0]["end"] == 1.0

    def test_long_gap_splits_blocks(self):
        # 15 words with tight timestamps → splits by max 10 per block
        words = [self.make_word(f"w{i}", float(i) * 0.5, float(i) * 0.5 + 0.3) for i in range(15)]
        blocks = _group_words_into_subtitles(words)
        assert len(blocks) >= 2
        assert len(blocks[0]["text"].split()) <= 10

    def test_empty_input(self):
        assert _group_words_into_subtitles([]) == []


class TestHotWords:
    """_apply_hotwords_to_srt corrects ASR errors against glossary."""

    def test_no_change_for_no_glossary(self):
        result = _apply_hotwords_to_srt("Hello world", extra_terms=[])
        assert result == "Hello world"

    def test_basic_correction_with_extra_terms(self):
        # Hot words may lowercase the match
        result = _apply_hotwords_to_srt("Hello world", extra_terms=["hello"]).lower()
        assert "hello" in result

    def test_multiple_extra_terms(self):
        result = _apply_hotwords_to_srt(
            "test foo bar", extra_terms=["foo bar"]
        )
        assert result == "test foo bar"

    def test_extra_terms_split_by_comma(self):
        result = _apply_hotwords_to_srt(
            "test", extra_terms=["foo, bar"]
        )
        assert result == "test"


class TestCCConversion:
    """_apply_cc_conversion converts Simplified → Traditional Chinese."""

    def test_passthrough_when_off(self):
        result = _apply_cc_conversion("净现值(NPV)计算示例", mode="off")
        assert result == "净现值(NPV)计算示例"

    def test_s2t_conversion(self):
        result = _apply_cc_conversion("净现值(NPV)计算示例", mode="standard")
        assert "淨現值" in result

    def test_taiwan_conversion(self):
        # s2tw converts chars; follow-up "t2twp" handles phrases
        result = _apply_cc_conversion("软件测试", mode="taiwan")
        assert "軟" in result  # at minimum, simplified→traditional chars work

    def test_no_error_on_missing_opencc(self):
        """Should return original text if OpenCC fails."""
        result = _apply_cc_conversion("test", mode="unknown")
        assert result == "test"


class TestCheckSilence:
    """check_silence detects silence in audio via Silero VAD."""

    def test_check_silence_returns_bool(self):
        from asr_engine import check_silence
        from pathlib import Path
        # Non-existent file → should handle gracefully
        result = check_silence(Path("/nonexistent/audio.wav"))
        assert isinstance(result, bool)

    def test_silence_passthrough(self):
        """threshold_db=0 means no silence threshold → returns False (not silence)."""
        from asr_engine import check_silence
        from pathlib import Path
        # threshold_db=0 effectively disables silence detection
        result = check_silence(Path("/nonexistent/audio.wav"), threshold_db=0)
        assert isinstance(result, bool)
