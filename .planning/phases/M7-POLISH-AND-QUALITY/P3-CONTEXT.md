# Phase 3: Backend Testing Expansion — Decisions

**Date:** 2026-07-17

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Target | ~70% coverage overall |
| Priority | `asr_engine.py` first (9% → ~70%) |
| Mock strategy | Mock MLX model + ffmpeg; test pure logic directly |
| New tests | 20+ for asr_engine, 5+ for server.py |
| Test type | Unit tests for pure functions, integration with mocks for API endpoints |

## Test Plan

### asr_engine.py (core, ~492 lines)
| # | Function | Tests | Approach |
|---|----------|-------|----------|
| 1 | `_seconds_to_srt_time` | 3 | Pure function, no deps |
| 2 | `_group_words_into_subtitles` | 3 | Pure function |
| 3 | `_apply_hotwords_to_srt` | 3 | Pure text replacement |
| 4 | `_apply_cc_conversion` | 3 | OpenCC, mock if unavailable |
| 5 | `check_silence` | 2 | Mock Silero VAD |
| 6 | `transcribe_one_video` | 2 | Mock MLX + ForcedAligner |
| 7 | `_align_and_format` | 2 | Mock ForcedAligner |

### server.py (endpoint coverage)
| # | Endpoint | Tests | Status |
|---|----------|-------|--------|
| 1 | `/endpoint/start` | already tested | ✅ |
| 2 | `/settings` read/write | 2 | 🆕 |
| 3 | `/cancel` | already tested | ✅ |
| 4 | `/models/status` | already tested | ✅ |
| 5 | `/waveform` | 1 | 🆕 (real ffmpeg) |
