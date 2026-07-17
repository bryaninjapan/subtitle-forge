# State — Subtitle Forge

## Project Status
```
Status: In Progress
Branch: feature/local-asr-qwen3
Current Phase: 健康清理（完成 HIGH，MEDIUM 暫緩）
Resumed: 2026-06-26
```

## Recent Commits
- `c5d58ca` feat: migrate ASR engine from Gemini API to local Qwen3-ASR-1.7B
- `27016ff` chore: stop tracking .claude/settings.json
- `1486313` fix: correct requirements.txt — add 6 missing deps, remove stdlib, pin versions

## Done
- [x] 掃描 codebase（gsd-map-codebase + gsd-scan）
- [x] 生成 CODEBASE-MAP.md + SCAN-REPORT.md
- [x] 3 項 HIGH 問題已修復
- [x] Spike 001 驗證通過
- [x] **Milestone 2: UX-1 User Experience 強化** (2026-07-17)
  - [x] ASR model 切換 1.7B → 0.6B (RAM 省 2GB+)
  - [x] CLI --interactive 引導模式
  - [x] CLI --completion zsh/bash 自動補全
  - [x] 桌面通知 (osascript)
  - [x] Web Dashboard 升級 (drop-zone upload, HTMX 即時進度, 任務歷史)
  - [x] 48 tests, code review passed
- [x] **Milestone 3: ASR Engine Phase A+B+C** (2026-07-17)
  - [x] ForcedAligner 字詞級時間戳
  - [x] Silero VAD 取代 ffmpeg silence check
  - [x] Speaker Diarization
  - [x] Hot Words 熱詞校正 (632 glossary terms)
  - [x] Script Matching (--script)
  - [x] Smart Line Splitting (語速感知)
  - [x] Speculative Decoding
  - [x] Async/Batch Parallelism
  - [x] Long Audio Chunking (>30min)
  - [x] 49 tests, all green
- [x] **Milestone 4: Dual Backend + UX Enhancements** (2026-07-17)
  - [x] on_progress callback (即時 ASR 進度)
  - [x] Batch burn-in (--burn + 雙語自動偵測)
  - [x] OpenRouter Whisper API backend
  - [x] Dual backend 一鍵切換 (local/api)
  - [x] 59 tests, all green

## Pending (MEDIUM — 可按需處理)
- Bare `except:` 靜默吞錯（15 處）
- Unused imports（10 個檔案）
- settings.yaml dead config（12 key 未讀取）
- 手動 .env 解析重複 → 改用 python-dotenv
- 測試覆蓋率極低
