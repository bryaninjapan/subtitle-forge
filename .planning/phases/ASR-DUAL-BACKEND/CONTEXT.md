# Phase: ASR Dual Backend + on_progress + Batch Burn-in

**Date:** 2026-07-17

## 🔒 Locked Decisions

### Scope — 做這三項

| # | 項目 | 決定 | 估計 |
|---|------|------|------|
| 1 | `return_chunks` | ❌ **跳過** — 跟 C3 chunking 重疊，效益有限 | — |
| 2 | `on_progress` callback | ✅ **做** — 即時轉錄進度回調 | ~1h |
| 3 | Batch burn-in (批量合成字幕) | ✅ **做** — 升級 `srt_burn.py` + `--burn` CLI 旗標 | ~2h |
| 4 | 雙 ASR Backend (local + API) | ✅ **做** — if/else 簡單切換 | ~3-4d |

### Dual Backend 架構

- **切換方式**: `settings.yaml` 加一行 `asr_backend: "local"` 或 `"api"`
- **第一版 API**: OpenRouter Whisper
- **Local 保留全部** A+B+C 功能（ForcedAligner, VAD, Diarization, Chunking, Speculative Decoding）
- **API 路線**: 送音檔 → OpenRouter → 統一格式 → 共用後處理
- **共用後處理**: 熱詞校正 + Smart Splitting + Script Matching + SRT 輸出（不分 backend）
- **ForcedAligner**: Local only（API 用自己的 word timestamps）
- **VAD**: 共用（API 前也跑，過濾靜音片段節省 API 費用）

### API Backend 規格

```
Input:  audio file path + language
Output: {text: str, words: [{start, end, text}], segments: [{start, end, text}]}

實作：
1. 用 OpenAI-compatible client call OpenRouter
2. 選用 whisper-large-v3 或 cheaper 模型
3. 回傳格式統一成跟 local backend 一致
```

### on_progress

- 加到 `_transcribe_with_qwen3_asr()` 的 `transcribe()` call
- Callback 內容：chunk 編號、進度百分比
- 優先餵給 `rich.console` 的進度顯示（TUI）
- Web Dashboard 也可以接（透過 server.py 的 SSE/輪詢）

### Batch Burn-in

- 升級 `srt_burn.py`：
  - 批次處理（多檔案）
  - 自動選擇 bilingual.srt（優先）或 .srt（fallback）
  - CLI `--burn` 旗標
  - 可設定字體大小（`--burn-font-size`）
- 輸出：`{影片名}_burned.mp4`

## ⏱️ 排程

```
Task 1: on_progress callback        ~1h    獨立
Task 2: Batch burn-in               ~2h    獨立
Task 3: settings.yaml + config      ~30m   雙 backend 前置
Task 4: OpenRouter API backend      ~3h    核心
Task 5: if/else 接線 + 測試         ~2h    整合
─────────────────────────────
總計:                               ~5-6天

可以串接做（確認每個 task 再下一步）。
```
