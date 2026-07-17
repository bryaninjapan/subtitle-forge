# Plan: ASR Dual Backend + on_progress + Batch Burn-in

## Goal

1. **on_progress** — 即時 ASR 轉錄進度（長音頻不再乾等）
2. **Batch burn-in** — 一次燒錄多個影片的硬字幕
3. **Dual ASR Backend** — `settings.yaml` 一鍵切換 Local / API ASR

## Done Criteria

- [x] `_transcribe_with_qwen3_asr()` 支援 `on_progress` callback，TUI 顯示即時進度
- [x] `--burn` CLI 旗標：批次燒錄 bilingual/單語字幕
- [x] `srt_burn.py` 支援批次 + 字體大小設定
- [x] `settings.yaml` 新增 `asr_backend: "local" | "api"`
- [x] `config.py` 新增 `ASR_BACKEND` 常數
- [x] OpenRouter Whisper API backend 可正確轉錄 + 回傳 word timestamps
- [x] Local/API 切換不影響現有功能（Local 路線完全不變）
- [x] 共用後處理（熱詞、Smart Splitting、SRT）雙 backend 皆適用
- [x] `pytest tests/ -x` 通過

## Tasks

| # | Task | Est. | Deps |
|---|------|------|------|
| 1 | on_progress callback | 1h | — |
| 2 | Batch burn-in: upgrade srt_burn.py + --burn CLI | 2h | — |
| 3 | settings.yaml + config.py: asr_backend | 30m | — |
| 4 | OpenRouter API backend | 3h | 3 |
| 5 | if/else wiring + integration test | 2h | 4 |
| 6 | Final verification | 30m | 1-5 |

## Task Details

### Task 1: on_progress callback

- Add `on_progress` param to `_transcribe_with_qwen3_asr()`:
  ```python
  def _transcribe_with_qwen3_asr(..., on_progress=None):
      result = transcribe(..., on_progress=on_progress)
  ```
- Create a default callback that prints to console using Rich progress
- Wire through `transcribe_files()` → `_process_one()`
- Show: "ASR: chunk 3/8 — 45%" in the TUI

### Task 2: Batch burn-in

- Upgrade `srt_burn.py`:
  - `batch_burn(video_paths, subtitle_dir, output_dir, font_size=24)` — 批量燒錄
  - 自動找 `{name}.bilingual.srt`（優先）或 `{name}.srt`（fallback）
- Add `--burn` flag to `main.py` parser:
  ```
  --burn              Burn subtitles into video after processing
  --burn-font-size    Font size for burned subtitles (default: 24)
  ```
- Wire in `main()` batch run: after ASR/translate complete, call batch_burn
- Handle progress output per file

### Task 3: settings.yaml + config.py

- Add to `settings.yaml`:
  ```yaml
  pipeline:
    asr_backend: "local"   # "local" or "api"
  ```
- Add to `config.py`:
  ```python
  ASR_BACKEND = pipe_c.get("asr_backend", "local")
  ```
- Also add API configs:
  ```yaml
  asr_api:
    provider: "openrouter"
    model: "openai/whisper-large-v3"
    api_key: "${OPENROUTER_API_KEY}"
  ```

### Task 4: OpenRouter API backend

- New file: `asr_api.py` (or inline in `asr_engine.py`)
- Function: `_transcribe_via_api(audio_path, language) -> str`
  - Read audio file, check size limit (OpenRouter ~25MB for Whisper)
  - If >25MB, use chunking (reuse C3 logic) or compress
  - Call OpenRouter via openai-compatible client
  - Parse response into SRT format
- Use `openai` Python package (already in requirements.txt)
- Handle: API errors, rate limits, timeouts
- Return format: same SRT as local backend (for shared post-processing)

### Task 5: if/else wiring

- In `_transcribe_with_qwen3_asr()`:
  ```python
  if ASR_BACKEND == "api":
      return _transcribe_via_api(audio_path, language)
  # else: existing local MLX path (unchanged)
  ```
- Ensure shared post-processing (hot words, smart splitting) runs after both
- Note: ForcedAligner only for local path
- Test: switch `asr_backend`, run same file, compare output

### Task 6: Final verification

- `main.py --help` shows new `--burn` flag
- `pytest tests/ -x` passes
- `settings.yaml` has `asr_backend` key
- Local path unchanged (no API call, no regression)
- API path: unit test with mock response (don't call real API in tests)

## Files Changed / Created

| File | Change |
|------|--------|
| `asr_engine.py` | on_progress param, if/else backend switch |
| `asr_api.py` | **New** — OpenRouter API backend |
| `srt_burn.py` | Upgrade to batch + font size |
| `config.py` | ASR_BACKEND, API config constants |
| `settings.yaml` | asr_backend, asr_api section |
| `main.py` | --burn, --burn-font-size flags |
| `requirements.txt` | openai (already present) |

## Rollback

```bash
git checkout -- asr_engine.py srt_burn.py config.py settings.yaml main.py
rm asr_api.py
```

## Commit Message

```
feat(asr): dual backend + on_progress + batch burn-in

- Add on_progress callback for real-time ASR progress in TUI
- Upgrade srt_burn.py: batch processing, bilingual auto-select, --burn CLI
- Add dual ASR backend: asr_backend: "local" | "api" in settings.yaml
- New OpenRouter Whisper API backend (_transcribe_via_api)
- Keep all A+B+C features for local path (ForcedAligner, VAD, diarization...)
- Shared post-processing (hot words, smart splitting, SRT) works for both
- --burn and --burn-font-size CLI flags
```
