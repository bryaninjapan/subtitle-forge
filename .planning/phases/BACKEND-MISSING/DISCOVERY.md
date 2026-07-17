# Discovery: Backend Enhancement — Mini Tool Feature Parity

**Date:** 2026-07-17
**Goal:** Add all missing backend endpoints & pipeline features before building React frontend.

## 1. Current State

```
音檔 → [ASR + ForcedAligner + 熱詞校正] → SRT
       ↓ (always runs)
       [翻譯 + 筆記 + 章節] → bilingual.srt + notes + chapters
```

**問題**: 翻譯/筆記/章節永遠執行，沒有 toggle 控制。

## 2. Target State

```
預設:
  音檔 → [ASR + 熱詞 + ForcedAligner] → SRT

開啟後才跑:
  [✓] 翻譯字幕     →  bilingual.srt
  [✓] 學習筆記     →  StudyNotes.md
  [✓] 章節生成     →  章節標記

可選輸入:
  [ ] 辨識提示 (script matching) → 提升準確度
```

API server 新增 endpoint:

```
GET  /waveform/<task_id>     → amplitude array (波形資料)
GET  /audio/<path>           → serve audio file 
GET  /timestamps/<task_id>   → [{word, start, end}]
GET  /endpoint/qrcode        → QR SVG
GET  /endpoint/status        → 端點狀態
POST /endpoint/start         → 啟動端點
POST /endpoint/stop          → 停止
GET  /models/status          → 模型列表 + 下載狀態
POST /models/download/:name  → 下載模型
POST /pipeline               → 執行 pipeline (可選 toggle 參數)
```

## 3. Phase Breakdown

### Phase 1: New API Endpoints (🟢 easy, ~1 day)

| # | Task | 說明 |
|---|------|------|
| 1 | `GET /audio/<path>` | Serve audio/video files for playback |
| 2 | `GET /waveform/<task_id>` | 回傳音訊 amplitude array |
| 3 | `GET /timestamps/<task_id>` | 回傳 ForcedAligner 產出的逐字時間戳 |
| 4 | `GET /endpoint/qrcode` | 產生 QR code SVG |
| 5 | `POST /pipeline` | 接受檔案 + toggle 參數，選擇性執行翻譯/筆記/章節 |

### Phase 2: Pipeline Toggle (🟡 medium, ~1 day)

| # | Task | 說明 |
|---|------|------|
| 6 | Pipeline refactor | 預設只跑 ASR，翻譯/筆記/章節由 toggle 控制 |
| 7 | VAD threshold → settings.yaml | 暴露 VAD 靈敏度參數 |
| 8 | OpenCC 簡繁轉換 | 加入 OpenCC library + config toggle |

### Phase 3: Model Management (🟡 medium, ~2 day)

| # | Task | 說明 |
|---|------|------|
| 9 | `GET /models/status` | 掃描 huggingface cache 回報模型狀態 |
| 10 | `POST /models/download/:name` | 觸發後台下載 |
| 11 | Model download progress | 即時下載進度 |

### Phase 4: Endpoint Service (🟡 medium, ~2 day)

| # | Task | 說明 |
|---|------|------|
| 12 | `POST /endpoint/start` / `stop` | 啟動/停止 background server |
| 13 | Access key management | 金鑰生成 + 驗證 |

### Phase 5: Real-time Recording (🔴 hard, deferred)

不包含在目前 scope，需要 streaming ASR library。
