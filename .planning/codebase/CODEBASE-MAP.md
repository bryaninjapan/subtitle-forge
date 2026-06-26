# Codebase Map — Subtitle Forge

## Overview

| 項目 | 內容 |
|------|------|
| **類型** | Monolithic CLI pipeline + Web Dashboard |
| **語言** | Python 3.12+ |
| **框架** | 無 Web 框架（Flask 僅用於 dashboard），CLI 驅動 |
| **Repo** | `github.com/bryaninjapan/subtitle-forge` |
| **總行數** | ~3,588 行 Python（28 個 .py 檔／10 個 package） |
| **用途** | CFA 課程影片 → 自動轉錄 → 中英雙語字幕 → 學習筆記 → Anki 詞彙卡 |

## Directory Structure

```text
subtitle-forge/
├── main.py                 # CLI 入口（argparse + watch mode + server mode）
├── director.py             # ★ CLI entry（thin — 只留 main()，引擎拆分到 director/）
├── director/               # ★ 多 Agent DAG 編排引擎（核心）[refactored ✓]
│   ├── __init__.py         #   重新 export: WorkflowEngine, AgentConfig
│   ├── engine.py           #   WorkflowEngine (573 行) + AgentConfig
│   └── state_store.py      #   StateStore — state.json 讀寫（獨立可測）
├── multi_agent_workflow.json  # DAG 定義（8 個 agent 的依賴圖）
├── config.py               # 全域配置（讀 settings.yaml + 環境變數）
├── settings.yaml           # YAML 設定檔（模型、並發數、成本上限）[dead key 已清除 ✓]
├── .env                    # API Keys（gitignored）
│
├── ── Pipeline Agents ──
├── preflight_agent.py      # 音頻提取（ffmpeg → 16kHz wav）
├── asr_engine.py           # 語音轉文字（本地 Qwen3-ASR-1.7B via mlx）
├── translator.py           # SRT 翻譯（OpenRouter API，批次並發）
├── srt_utils.py            # SRT 解析/合併/雙語/清理/VTT 轉換
├── vision_engine.py        # 關鍵幀提取（ffmpeg，自適應間隔）
├── notes_generator.py      # 學習筆記生成（Gemini + 關鍵幀）
├── chapter_generator.py    # YouTube 章節時間戳（OpenRouter）
├── qa_agent.py             # 翻譯品質評分（LLM-as-a-judge）
│
├── ── API Clients ──
├── gemini_client.py        # Google Gemini singleton client [dotenv 整合 ✓]
├── openrouter_client.py    # OpenRouter singleton client [dotenv 整合 ✓]
│
├── ── Supporting Modules ──
├── glossary_manager.py     # CFA 詞彙表自動提取/更新（Gemini）
├── glossary.json           # 詞彙表資料（~53KB）
├── usage_tracker.py        # Token 用量 & 成本追蹤（JSONL log）
├── media_utils.py          # 媒體工具（時長、hash、ffmpeg wrapper）
├── anki_exporter.py        # 詞彙表 → Anki .apkg 匯出
├── pdf_generator.py        # 關鍵幀 → PDF 投影片
│
├── ── Operations ──
├── recover.py              # 零 API 修復引擎（偵測缺失產物、本地修補）
├── check_status.py         # Pipeline 狀態檢查（Rich 表格輸出）
├── wipe_outputs.py         # 清空 output 目錄
├── server.py               # Flask Web Dashboard（port 5000）
│
├── ── Config & CI ──
├── requirements.txt        # 依賴（google-genai, openai, python-dotenv, pyyaml...）
├── .github/workflows/test.yml  # GitHub Actions CI
├── .env                    # API Keys（GEMINI_API_KEY, OPENROUTER_API_KEY）
│
├── tests/
│   ├── test_srt.py         # SRT 解析/清理/VTT（3 tests）[不變]
│   ├── test_director.py    # WorkflowEngine smoke test（3 tests）[新增]
│   └── test_state_store.py # StateStore unit test（19 tests）[新增]
│
├── input/                  # 影片輸入目錄（watch mode 監聽此處）
├── output/                 # 產物輸出目錄（每影片一子資料夾）
│   └── {video_stem}/
│       ├── state.json      # ★ Agent 狀態持久化
│       ├── {stem}_16k.wav  # 提取的音頻
│       ├── {stem}.srt      # 原始英文字幕
│       ├── {stem}.zh.srt   # 中文字幕
│       ├── {stem}.bilingual.srt  # 雙語字幕
│       ├── {stem}.studynotes.md  # 學習筆記
│       ├── {stem}.chapter.txt    # 章節時間戳
│       └── frames/         # 提取的關鍵幀 .jpg
│
├── spikes/                 # 技術驗證報告（保留參考）
│   ├── 001-requirements-fix/
│   └── 002-unused-imports/
│
└── venv/                   # 虛擬環境（gitignored）
```

## Architecture Pattern

**Multi-Agent DAG Orchestration** — 核心 Director Engine 解析 `multi_agent_workflow.json` 定義的 8-agent 有向無環圖，按依賴關係並發執行。

### DAG 拓撲

```text
                    preflight_agent
                   /              \
          vision_agent           asr_agent
              |                     |
              +--------+------------+
                       |
              translation_agent
                   /        \
         bilingual_agent   qa_judge_agent

  asr_agent ──→ chapter_agent
  asr_agent ──→ study_notes_agent (also needs vision_agent)
```

### Agent 清單

| Agent ID | 動作 | 依賴 | API |
|----------|------|------|-----|
| `preflight_agent` | extract_audio_and_validate | — | ffmpeg (local) |
| `vision_agent` | extract_keyframes | preflight | ffmpeg (local) |
| `asr_agent` | transcribe_audio | preflight | Qwen3-ASR-1.7B (local MLX) |
| `translation_agent` | translate_srt | asr + vision | OpenRouter (cloud) |
| `bilingual_agent` | create_bilingual_srt | translation | local (srt_utils) |
| `study_notes_agent` | generate_study_notes | asr + vision | Gemini (cloud) |
| `chapter_agent` | generate_video_chapters | asr | OpenRouter (cloud) |
| `qa_judge_agent` | score_translation | translation | OpenRouter (cloud) |

### 執行模式

- **並發 DAG**：`ThreadPoolExecutor(max_workers=5)` 同時處理多影片
- **每影片內**：按依賴順序，同層 agent 並發執行（如 vision + asr 可並行）
- **狀態持久化**：`state.json` per video（via `StateStore`），記錄每個 agent 的 status + outputs
- **Bootstrap from disk**：每次 run 先檢查產物檔案是否已存在，已完成的不重跑
- **重試策略**：
  - In-session retry：`max_retries` + exponential backoff
  - Cross-session retry：最多 3 次（`MAX_CROSS_SESSION_RETRIES`）
  - Permanent error（400/token limit）：永不重試
  - 達上限 → `FAILED_MAX_RETRIES`，進入 Review Queue 需人工介入

## Entry Points

| 入口 | 說明 |
|------|------|
| `python main.py [paths]` | 批次處理媒體檔案 |
| `python main.py --watch` | 監聽 `input/` 目錄，新檔自動處理 |
| `python main.py --server` | 啟動 Flask Web Dashboard (port 5000) |
| `python main.py --dry-run` | 預覽待處理檔案，不呼叫 API |
| `python main.py --wipe` | 清空 output 目錄 |
| `python director.py` | 直接執行 DAG engine（thin entry，僅 CLI main） |
| `python recover.py` | 零 API 修復缺失產物 |
| `python check_status.py` | 查看所有影片的 pipeline 狀態 |

## Key Patterns

| 面向 | 模式 |
|------|------|
| **編排** | DAG engine 讀 JSON 定義 → 動態 dispatch action → Python function |
| **套件結構** | `director/` package 取代單一 director.py（StateStore 獨立 module） |
| **API Client** | Thread-safe singleton（`gemini_client.py`, `openrouter_client.py`） |
| **環境變數** | `python-dotenv` 統一載入 `.env`（不再手動解析） |
| **ASR** | 本地 Qwen3-ASR-1.7B via MLX（無 GPU 需求，Apple Silicon 原生） |
| **翻譯** | OpenRouter API，SRT 批次切割（batch_size=50），ThreadPoolExecutor 並發 |
| **狀態管理** | `StateStore` — JSON 持久化 + threading.Lock（72 行，獨立可測） |
| **成本控制** | `usage_tracker.py` 記 JSONL log，`max_cost_usd` 上限可配 |
| **詞彙表** | `glossary.json` 動態增長，Gemini 自動提取 CFA 術語 → Anki 匯出 |
| **錯誤分類** | Permanent（不重試）vs Transient（重試）vs Max-Retries（人工 review） |
| **例外處理** | 所有 bare `except:` 已替換為特定 exception type |
| **復原** | `recover.py` 零 API 掃描 + 本地修補（重命名、合併、重建 SRT） |
| **CLI UI** | Rich library（Progress bar, Table, Panel, Console） |
| **測試** | pytest，25 tests（3 srt + 3 director + 19 state_store） |

## Testing

| 檔案 | Tests | 涵蓋範圍 |
|------|-------|---------|
| `tests/test_srt.py` | 3 | SRT 解析、文字清理、VTT 轉換 |
| `tests/test_director.py` | 3 | WorkflowEngine 初始化、agent 解析（smoke test） |
| `tests/test_state_store.py` | 19 | StateStore 全部 public API + thread safety |
| **Total** | **25** | |

**之前從 3 個 test 成長到 25 個，但仍有大量 module 無測試。**

## Dependencies

### Python 套件

| 套件 | 用途 |
|------|------|
| `google-genai` | Google Gemini API SDK |
| `openai` | OpenRouter API（OpenAI-compatible client） |
| `python-dotenv` | ✅ 實際載入 `.env` API Keys |
| `pyyaml` | 讀取 `settings.yaml` |
| `rich` | CLI 美化（Progress, Table, Panel） |
| `watchdog` | 檔案系統監聽（watch mode） |
| `genanki` | Anki .apkg 詞彙卡匯出 |
| `flask` | Web Dashboard |
| `pytest` + `pytest-cov` | 測試框架 + 覆蓋率報告 |
| `mlx-qwen3-asr` | 本地 ASR 推理（Apple Silicon） |

### 外部工具

| 工具 | 用途 |
|------|------|
| `ffmpeg` / `ffprobe` | 音頻提取、關鍵幀截取、媒體時長探測 |

### 外部 API

| API | 用途 | 模型 |
|-----|------|------|
| Google Gemini | 學習筆記生成、詞彙提取 | gemini-2.5-flash |
| OpenRouter | 翻譯、章節生成、QA 評分 | deepseek-chat-v3-0324 |

## Config

| 檔案 | 說明 |
|------|------|
| `settings.yaml` | 模型選擇、並發數、成本上限（無 dead config） |
| `.env` | `GEMINI_API_KEY`, `OPENROUTER_API_KEY` |
| `multi_agent_workflow.json` | DAG 定義（8 agent, action→function mapping） |

## Git History（近 10 commits）

```text
5cf668f test: add 19 unit tests for StateStore (6→25 tests)
b84bb92 refactor: split director.py into director/ package (3.1)
5dc9328 chore: remove 12 dead config keys from settings.yaml (3.6)
a77c09a fix: add from __future__ import annotations for Python 3.9 compat (2.4)
8f1d908 refactor: unify .env loading via python-dotenv (3.4)
ba9f9a9 chore: untrack build artifacts + update .gitignore
f2dba6c fix: replace all 12 bare except: with specific exception types
6ae5e91 chore: remove unused imports across 13 files
1486313 fix: correct requirements.txt — add 6 missing deps, remove stdlib, pin versions
27016ff chore: stop tracking .claude/settings.json
c5d58ca feat: migrate ASR engine from Gemini API to local Qwen3-ASR-1.7B (MLX)
```

## Notable Design Decisions

1. **混合本地/雲端 ASR**：從 Gemini 雲端 ASR 遷移到本地 Qwen3-ASR-1.7B（MLX），降低 API 成本
2. **Cross-session retry**：狀態持久化讓失敗的 agent 可在下次 run 時重試，而非從頭開始
3. **Bootstrap from disk**：優先從檔案系統恢復已完成的工作，避免重複 API 呼叫
4. **CFA 專用**：翻譯 prompt 和詞彙表都針對 CFA 考試內容客製化
5. **成本追蹤**：每次 API 呼叫記 JSONL log，可設 `max_cost_usd` 硬上限
6. **Recover engine**：獨立的 `recover.py` 可在零 API 呼叫下修復大部分缺失產物
7. **director.py 拆分**：從 575 行單一檔案重構成 `director/` package，StateStore 獨立可測
8. **Codebase cleanup**：移除 12 個 dead config key、統一 .env 載入、移除所有 bare except
