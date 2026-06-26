# Pause Record: Subtitle Forge 健康清理

## Paused: 2026-06-26

## Current Task
掃描報告問題處理 — 已完成 3 項 HIGH，剩餘 MEDIUM 項目暫緩

## Progress
- ✓ 掃描 codebase（gsd-map-codebase + gsd-scan）
- ✓ 生成 CODEBASE-MAP.md + SCAN-REPORT.md
- ✓ Commit asr_engine.py 未 commit 變更（c5d58ca）
- ✓ 移除 .claude/settings.json from git tracking（27016ff）
- ✓ 修正 requirements.txt — 補 6 個缺失套件、刪 stdlib、pin 版本（1486313）
- ✓ Spike 001 驗證 requirements.txt 修正不會搞垮專案（VALIDATED）

## Next Steps
掃描報告中剩餘的 MEDIUM 項目（不急，可按需處理）：
1. **Bare `except:` 靜默吞錯**（15 處）— 最值得修的，director.py:82 和 config.py:91
2. **Unused imports**（10 個檔案）— 機械式清理
3. **settings.yaml dead config**（12 個 key 從未被讀取）— 決定刪除還是接上
4. **手動 .env 解析重複** — 改用 python-dotenv 統一
5. **測試覆蓋率極低** — 補 director.py DAG 邏輯測試

## Blockers
無

## Context Needed on Resume
- Branch: `feature/local-asr-qwen3`（不 merge main，main 保留 Gemini 舊版）
- 3 個 commit 已提交：c5d58ca, 27016ff, 1486313
- Spike 目錄: `spikes/001-requirements-fix/`（保留參考）
- 掃描報告: `.planning/codebase/SCAN-REPORT.md`
- 用戶決定：保留 git-tracked artifacts（cfa_glossary.apkg 等），只移除了 .claude/settings.json
- 用戶決定：不合併 feature branch → main
