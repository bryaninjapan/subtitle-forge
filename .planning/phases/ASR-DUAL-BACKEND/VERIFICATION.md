# Phase: ASR Dual Backend + on_progress + Batch Burn-in — Verification

**Status:** ✅ Passed

## Test Results

```
59 passed, 1 warning in 0.69s
```

## Task → Test Mapping

| # | Task | Test Evidence | Status |
|---|------|---------------|--------|
| 1 | on_progress callback | `_default_progress_cb` callable, `on_progress` param in `_transcribe_with_qwen3_asr`, wired to `mlx_qwen3_asr.transcribe()` | ✅ |
| 2 | Batch burn-in | `srt_burn.batch_burn`, `find_best_subtitle`, `burn_subtitles` — 5 unit tests (subtitle priority, graceful error, CLI flags) | ✅ |
| 3 | settings.yaml + config | `ASR_BACKEND`, `ASR_API_PROVIDER`, `ASR_API_MODEL`, `ASR_API_KEY_ENV` in config.py + settings.yaml | ✅ |
| 4 | OpenRouter API backend | `asr_api.py` with `transcribe_via_api`, `_compress_audio`, `_extract_segments_from_response` — 4 unit tests (SRT formatting, no-key error, empty response) | ✅ |
| 5 | if/else wiring | `_transcribe_with_qwen3_asr` contains `ASR_BACKEND == "api"` check, `transcribe_via_api` call, `_apply_hotwords_to_srt` for API path | ✅ |
| 6 | Final verification | 59 tests pass, `--burn` in --help, all done criteria met | ✅ |

## Manual Checks

| Check | Result |
|-------|--------|
| `main.py --help` shows `--burn`, `--burn-font-size` | ✅ |
| `settings.yaml` has `asr_backend` key | ✅ |
| Local backend unchanged (no API regression) | ✅ |
| Hot words correction runs for both local and API | ✅ |
| `asr_api.py` handles missing API key gracefully | ✅ |

## Files Changed / Created

| File | Status | Lines |
|------|--------|-------|
| `asr_engine.py` | Modified | on_progress + if/else backend switch |
| `asr_api.py` | **New** | 210 lines — OpenRouter API backend |
| `srt_burn.py` | Modified | batch + font size + bilingual detection |
| `config.py` | Modified | ASR_BACKEND + API config constants |
| `settings.yaml` | Modified | asr_backend + asr_api section |
| `main.py` | Modified | --burn + --burn-font-size flags |
| `tests/test_cli_server.py` | Modified | 11 new tests for all new features |

## Known Gaps

| Gap | Priority | Note |
|-----|----------|------|
| API backend only tested with unit tests (no real API call) | LOW | Real API test requires `OPENROUTER_API_KEY` env var |
| API backend chunking for files >25MB only uses compression, not splitting | LOW | Can be enhanced if needed |
| `on_progress` callback from chunked path uses chunk counter, not MLX native | LOW | Chunk-level progress works but isn't as granular |

## Cross-Reference

```
PLAN.md (6 tasks) ←→ Implementation (6 tasks done) ←→ Tests (59 tests)
```

All 6 tasks in PLAN.md are implemented and verified. No orphaned tasks. No scope drift.
