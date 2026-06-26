# Codebase Scan Report — Subtitle Forge

```
══════════════════════════════════════════════════════════════
                    CODEBASE SCAN REPORT
══════════════════════════════════════════════════════════════

Scan Date: 2026-06-26
Project:   subtitle-forge
Branch:    feature/local-asr-qwen3 (1 commit ahead of main, NOT merged)
Last Commit: 2026-04-09 (2.5 months ago)
Files Scanned: 22 Python + 3 shell + config files
Tests: 3/3 PASSED (pytest, srt_utils only)

══════════════════════════════════════════════════════════════
 ISSUES FOUND
══════════════════════════════════════════════════════════════
```

## 1. 🔴 Git Hygiene — HIGH

| # | 問題 | 詳情 |
|---|------|------|
| 1.1 | **Feature branch 未合併** | `feature/local-asr-qwen3` 領先 main 1 commit，Qwen3-ASR 遷移已完成但未 merge |
| 1.2 | **未提交的修改** | `asr_engine.py` 有 97 insert / 124 delete 的未 commit 變更 |
| 1.3 | **大量 build artifact 被 git tracked** | `cfa_glossary.apkg` (188K), `usage_log.jsonl` (176K), `pipeline_failures.md` (527K), `pipeline_report.md` (117K), `cost_history.md`, `usage_sample_*.json` — 共 ~1MB 垃圾在 repo 裡 |
| 1.4 | **`.gitignore` 不完整** | `pipeline_failures.md`, `pipeline_report.md`, `cost_history.md`, `usage_sample_*.json` 未被 ignore |
| 1.5 | **`.claude/settings.json` 被 tracked** | Claude Code 的本地設定不該進 repo |

## 2. 🟡 Dependencies — MEDIUM

| # | 問題 | 詳情 |
|---|------|------|
| 2.1 | **`requirements.txt` 嚴重不完整** | 實際用到但沒列：`pyyaml`, `rich`, `watchdog`, `genanki`, `flask`, `pytest` — 全部缺失 |
| 2.2 | **`requirements.txt` 含 stdlib 套件** | `pathlib` 和 `argparse` 是 Python 標準庫，不該出現 |
| 2.3 | **無 `requirements.lock` / 無 pin 版本** | 所有依賴都無版本號，`pip install -r` 結果不可重現 |
| 2.4 | **venv 用 Python 3.12，系統是 3.9** | `from __future__ import annotations` 有加但部分檔案（`config.py` L23: `dict[str, Any]`）在 3.9 會 crash |

## 3. 🟡 Code Smells — MEDIUM

| # | 問題 | 詳情 |
|---|------|------|
| 3.1 | **5 個檔案 >300 行** | `director.py` (578), `recover.py` (396), `srt_utils.py` (342), `translator.py` (337), `asr_engine.py` (314) |
| 3.2 | **15 處 bare `except:` / `except Exception:`** | 靜默吞錯，最嚴重：`director.py:82 except: pass`（state.json 載入失敗無聲）、`config.py:91 except: return {}`（glossary 載入失敗無聲） |
| 3.3 | **10 個檔案有 unused imports** | `director.py` (4個), `main.py` (2個), `srt_utils.py` (3個), 等 |
| 3.4 | **手動 `.env` 解析重複** | `gemini_client.py` 和 `openrouter_client.py` 各自手動讀 `.env`，但 `requirements.txt` 有 `python-dotenv` 卻沒用到 |
| 3.5 | **`print()` vs `console.print()` 混用** | `asr_engine.py` 用 `print()`，其他模組用 `rich.console` — 輸出格式不一致 |
| 3.6 | **`settings.yaml` 多個設定未被讀取** | `burn_subtitles`, `slide_pdf`, `structured_json`, `bilingual`, `webvtt`, `validation`, `study_notes`, `chapters`, `difficulty_level`, `max_asr_terms`, `hit_threshold`, `prune_after_runs` — config.py 沒讀這些 key，等於 dead config |

## 4. 🟢 Security — LOW

| # | 問題 | 詳情 |
|---|------|------|
| 4.1 | **`.env` 未被 tracked** | ✅ 正確（`.gitignore` 有 `.env`） |
| 4.2 | **無 hardcoded secrets** | ✅ API keys 全走 `os.environ` |
| 4.3 | **無 `shell=True`** | ✅ 所有 subprocess 呼叫都用 list form |
| 4.4 | **無 `eval()` / `exec()`** | ✅ |
| 4.5 | **無 SQL injection 風險** | ✅（無 DB 使用） |

## 5. 🟡 Testing — MEDIUM

| # | 問題 | 詳情 |
|---|------|------|
| 5.1 | **測試覆蓋率極低** | 僅 `srt_utils.py` 有 3 個測試，其餘 21 個模組 0 測試 |
| 5.2 | **無 integration test** | DAG engine (`director.py`) 是核心但完全無測試 |
| 5.3 | **CI 配置的 Python 版本和 venv 不一致** | CI 用 3.12，但 `requirements.txt` 缺依賴，CI 可能跑不過 |

## 6. 🟢 TODOs/FIXMEs — NONE

掃描結果：0 個 TODO/FIXME/XXX/HACK — 程式碼中無技術債標記。

```
══════════════════════════════════════════════════════════════
 SUMMARY
══════════════════════════════════════════════════════════════

Severity:
  🔴 HIGH:   5 (git hygiene)
  🟡 MEDIUM: 12 (deps, code smells, testing)
  🟢 LOW:    0 (security clean)

Top Priority Actions:
  1. 合併 feature/local-asr-qwen3 → main（或 rebase 後合併）
  2. 提交或 stash asr_engine.py 的未 commit 變更
  3. 清理 git-tracked artifacts + 補 .gitignore
  4. 修 requirements.txt（加缺失套件、刪 stdlib、pin 版本）
  5. 補測試（至少 director.py 的 DAG 邏輯）

══════════════════════════════════════════════════════════════
```
