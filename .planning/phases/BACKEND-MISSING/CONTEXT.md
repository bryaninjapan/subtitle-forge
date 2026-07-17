# CONTEXT: Backend Enhancement — Mini Tool Feature Parity

**Date:** 2026-07-17

## 🔒 Locked Decisions

### Pipeline
- 預設只跑 ASR，翻譯/筆記/章節由 toggle 控制 (`settings.yaml`)
- `POST /pipeline` 接受 `{file, translate, notes, chapters, prompt}` 參數

### Waveform
- Server 端預算 amplitude peaks
- 動態取樣：<1min→50pts/s, <10min→10pts/s, >10min→cap 10000pts

### Audio Serving
- Flask `send_file` + Range header 支援跳播

### Word Timestamps
- ASR 完成後將 ForcedAligner 產出的 word timestamps 存為 JSON
- `GET /timestamps/<task_id>` 回傳

### QR Code
- `qrcode` Python library，`GET /endpoint/qrcode` 回傳 PNG

### Hot Words
- 保留 `asr_hotwords` 開關，glossary 改為通用錯詞表
- 自訂詞庫等 UI 做好再補

### Prompt / Script Matching
- `POST /pipeline` 接受 `prompt` 字串，整合 hot words + reference text

### Endpoint
- 啟動/停止 server、金鑰管理、Cloudflare tunnel（Phase 4）

### Real-time Recording
- 🔴 延後，不做
