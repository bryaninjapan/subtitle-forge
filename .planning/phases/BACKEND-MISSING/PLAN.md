# Plan: Backend Enhancement — Mini Tool Feature Parity

## Goal

Add all missing backend endpoints & pipeline features before building React frontend.

4 phases, ~6 days. Serial execution.

---

## Phase 1: New API Endpoints (~1.5 day)

### Done Criteria
- [ ] `GET /audio/<path>` serves audio/video files with Range header
- [ ] `GET /waveform/<task_id>` returns adaptive-resolution amplitude peaks
- [ ] `GET /timestamps/<task_id>` returns word-level timestamps JSON from ForcedAligner
- [ ] `GET /endpoint/qrcode` returns QR code PNG for server URL
- [ ] `POST /pipeline` accepts file + toggle params, runs selective pipeline
- [ ] ForcedAligner word timestamps saved as JSON during ASR

| # | Task | Est. | Description |
|---|------|------|-------------|
| P1-1 | `GET /audio/<path>` | 30m | `send_file` with `conditional=True` |
| P1-2 | `GET /waveform/<task_id>` | 1h | ffmpeg → raw audio → downsample to adaptive peaks |
| P1-3 | Save word timestamps as JSON | 30m | Modify `_align_and_format()` to write `.words.json` |
| P1-4 | `GET /timestamps/<task_id>` | 30m | Read `.words.json` and return |
| P1-5 | `GET /endpoint/qrcode` | 30m | `qrcode.make(url)` → PNG response |
| P1-6 | `POST /pipeline` | 1h | Accept `{file, translate, notes, chapters, prompt}` |

### Rollback (P1)
```bash
git checkout -- server.py asr_engine.py config.py
```

---

## Phase 2: Pipeline Refactor + Settings (~1.5 day)

### Done Criteria
- [ ] Pipeline 預設只跑 ASR，翻譯/筆記/章節由 toggle 控制
- [ ] `settings.yaml` 有 `translate`, `study_notes`, `chapters` keys
- [ ] VAD threshold 可調
- [ ] OpenCC 簡繁轉換
- [ ] `prompt` 文字整合進 hot words / ForcedAligner

| # | Task | Est. | Description |
|---|------|------|-------------|
| P2-1 | Pipeline toggle refactor | 2h | `WorkflowEngine` 讀 toggle, 跳過對應 agent |
| P2-2 | `settings.yaml` + config.py toggles | 30m | `pipeline.translate`, `.study_notes`, `.chapters` |
| P2-3 | VAD threshold → settings | 30m | `vad_threshold: 0.35` |
| P2-4 | OpenCC conversion | 1h | `pip install opencc-python`, post-processing pass |
| P2-5 | Prompt → hot words wiring | 1h | `POST /pipeline prompt` 餵進 `_apply_hotwords_to_srt` |

### Rollback (P2)
```bash
git checkout -- server.py asr_engine.py config.py settings.yaml director/
```

---

## Phase 3: Model Management (~2 days)

### Done Criteria
- [ ] `GET /models/status` returns all model states (cached/pending/downloading/error)
- [ ] `POST /models/download/:name` triggers background download
- [ ] Download progress via `/progress` polling

| # | Task | Est. | Description |
|---|------|------|-------------|
| P3-1 | Scan huggingface cache for models | 1h | `huggingface_hub` scan `~/.cache/huggingface/` |
| P3-2 | `GET /models/status` | 1h | Return list with name, size, status |
| P3-3 | `POST /models/download/:name` | 2h | Threaded download with progress |
| P3-4 | Download progress → `/progress` | 1h | Wire model download into progress_store |

### Rollback (P3)
```bash
git checkout -- server.py
```

---

## Phase 4: Endpoint Service (~2 days)

### Done Criteria
- [ ] `POST /endpoint/start` launches a listener server
- [ ] `POST /endpoint/stop` kills the listener
- [ ] Access key generation + validation middleware
- [ ] Cloudflare tunnel (`cloudflared`) optional

| # | Task | Est. | Description |
|---|------|------|-------------|
| P4-1 | Listener server thread | 2h | Spawn subprocess running same Flask on different port |
| P4-2 | Access key auth middleware | 1h | API key check on upload endpoints |
| P4-3 | `cloudflared` subprocess | 2h | Spawn `cloudflared tunnel --url ...` |

### Rollback (P4)
```bash
git checkout -- server.py config.py settings.yaml
```

---

## Dependency Graph

```
Phase 1 (獨立)
├── P1-1 ~ P1-6 串接
│
Phase 2 (依賴 P1-6 的 POST /pipeline)
├── P2-1 ~ P2-5 串接
│
Phase 3 (獨立)
├── P3-1 ~ P3-4 串接
│
Phase 4 (依賴 endpoint endpoint 概念, 可與 P3 並行)
├── P4-1 ~ P4-3 串接
```

**Critical Path**: P1 → P2 → P3/P4 (parallel) = ~5 days

---

## 執行順序

串接做：Phase 1 → Phase 2 → Phase 3 → Phase 4
