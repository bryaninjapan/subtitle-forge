# Milestone Archive: ASR Engine Enhancement — Phase A + B + C

**Completed:** 2026-07-17
**Branch:** `feature/local-asr-qwen3` (not merged to main)

## Goal

Upgrade subtitle-forge's local ASR engine with word-level alignment, hot words, VAD, diarization, script matching, smart splitting, and performance optimizations.

## Phases Completed

| Wave | Phase | Tasks | Status |
|------|-------|-------|--------|
| 1 | A-2 + C2 | A4 (model→settings.yaml), A2 (Silero VAD), A3 (Diarization), C2 (Async batch) | ✅ |
| 2 | A-1 + C1 + C3 | A1 (ForcedAligner), C1 (Speculative Decoding), C3 (Long Audio Chunking) | ✅ |
| 3 | B | B1 (Hot Words), B2 (Script Matching), B3 (Smart Line Splitting) | ✅ |

## Deliverables

### ASR Engine
| Feature | Key Change | File |
|---------|-----------|------|
| Model config externalised | `QWEN3_ASR_MODEL` → `settings.yaml` | `asr_engine.py`, `config.py`, `settings.yaml` |
| ForcedAligner word-level timestamps | `_align_and_format()`, `_group_aligned_words_into_subtitles()` | `asr_engine.py` |
| Silero VAD | Replaced ffmpeg silencedetect | `asr_engine.py` |
| Speaker Diarization | `diarize=True` → `[Speaker 1]` labels | `asr_engine.py` |
| Hot Words glossary correction | 632 terms extracted from glossary, case-insensitive + spaced acronym | `asr_engine.py` |
| Script Matching | `--script` flag, ForcedAligner on reference text | `asr_engine.py`, `main.py` |
| Smart Line Splitting | Speaking-rate-aware, sentence-boundary-preferring | `asr_engine.py` |
| Speculative Decoding | `draft_model` for audio >10min | `asr_engine.py` |
| Async/Batch Parallel | `ThreadPoolExecutor` with configurable concurrency | `asr_engine.py` |
| Long Audio Chunking | 10-min chunks, 3s overlap, dedup merge | `asr_engine.py` |

### New Settings (`settings.yaml`)
```yaml
pipeline:
  asr_model: "Qwen/Qwen3-ASR-0.6B"
  asr_aligner_model: "Qwen/Qwen3-ForcedAligner-0.6B"
  asr_diarize: false
  asr_diarize_num_speakers:
  asr_use_draft: false
  asr_hotwords: true
```

## Testing Status

- Before: 49 tests
- After: **49 tests** (no regressions)
- New test: `test_check_silence_fallback_on_empty_audio`

## Files Changed

| File | Insertions | Description |
|------|-----------|-------------|
| `asr_engine.py` | +545 | All 10 features |
| `config.py` | +6 | New config constants |
| `settings.yaml` | +6 | New pipeline settings |
| `main.py` | +265 | UX-1 + --script flag |

## Key Decisions

- **方案3**: ForcedAligner + glossary correction (not modifying mlx_qwen3_asr library)
- **osascript over terminal-notifier**: Built-in macOS notification, no install needed
- **HTMX over SSE**: Simpler, zero dependencies for web dashboard
- **hot words from glossary abbreviations**: "Net Present Value (NPV)" → extracts "NPV"
- **smart splitting per speaking rate**: Fast speech → shorter lines for readability

## Learnings

1. **ForcedAligner alignment takes numpy array, not file path** — `align(audio_np, text, language)`
2. **Glossary keys are full phrases with parenthesized abbreviations** — need parsing to extract short forms
3. **Chunk overlap of 3 seconds** is sufficient to avoid cut-off words at boundaries
4. **ThreadPoolExecutor is safe** when each file has its own output directory
5. **Silero VAD is much more accurate** than ffmpeg silencedetect but requires torch
