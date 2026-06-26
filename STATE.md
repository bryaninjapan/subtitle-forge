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

## Pending (MEDIUM — 可按需處理)
- Bare `except:` 靜默吞錯（15 處）
- Unused imports（10 個檔案）
- settings.yaml dead config（12 key 未讀取）
- 手動 .env 解析重複 → 改用 python-dotenv
- 測試覆蓋率極低
