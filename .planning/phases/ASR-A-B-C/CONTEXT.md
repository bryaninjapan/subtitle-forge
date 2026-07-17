# ASR Engine Enhancement — Phase A + B + C

**Date:** 2026-07-17
**Estimate:** ~2 weeks (10 tasks)

## Locked Decisions

### 技術方向
- **熱詞方案**：方案 3 — ForcedAligner + glossary 校正（非修改 library）
- **VAD**：Silero VAD 取代 ffmpeg silencedetect
- **Diarization**：`mlx_qwen3_asr` 內建 `diarize=True`
- **多領域 glossary**：待 Phase B 時決定（單檔 / 多檔案）

### 依賴關係

```
A4: settings.yaml model path ──→ A1: ForcedAligner ──→ B1: 熱詞注入
                                    │
                                    ├──→ B2: 文稿匹配
                                    └──→ B3: 智能拆行

A2: VAD ── (可與 A1 並行)
A3: Diarization ── (可與 A1 並行)

C1: Speculative decoding ── (依賴 model 載入，其餘獨立)
C2: Async/batch ── (獨立)
C3: Long audio chunking ── (獨立)
```

### Scope

| Phase | Tasks | Est. |
|-------|-------|------|
| A-1 | A4 + A1 + B1 (ForcedAligner + 熱詞) | 3 days |
| A-2 | A2 + A3 (VAD + Diarization) | 2 days |
| B | B2 + B3 (文稿匹配 + 智能拆行) | 3 days |
| C | C1 + C2 + C3 (效能優化) | 3 days |

### 關鍵檔案
- `asr_engine.py` — 主要修改檔案
- `config.py` / `settings.yaml` — model 路徑外置
- `srt_utils.py` — 智能拆行演算法
- `director/engine.py` — async batch 支援
