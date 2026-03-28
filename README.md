# Subtitle Forge

CFA 教學影片自動化處理工具，透過 Gemini API 完成語音辨識、中文字幕翻譯、學習筆記生成與 LOS 章節標記。

---

## 🚀 2026 旗艦級優化功能 (Enterprise Production Ready)

本專案已完全進化為具備高可靠性、成本透明度與專業輸出能力的生產環境工具：

### 1. 視覺與體驗 (Next-Gen Experience)
*   **Rich TUI 進度終端**：具備動態進度條、狀態旋轉圖標與作業分工顯示，徹底告別混亂的捲動 Log。
*   **--dry-run 成本預報**：在執行前，系統會根據影片時長自動計算 **ASR + 翻譯 + 多模態分析** 的預估美金費用。
*   **Web Dashboard**：執行 `./venv/bin/python3 main.py --server` 即可開啟網頁看板，即時監控歷史任務用量與檔案狀況。

### 2. 品質與格式 (Professional Outputs)
*   **雙語字幕自動合稿 (.bilingual.srt)**：翻譯完成後自動生成英中對照字幕，完美支援 CFA 學員對應原文學習。
*   **WebVTT 支援 (.vtt)**：為了現代瀏覽器相容性，自動生成 .vtt 格式，方便直接在網頁播放器掛載。
*   **輸出完整度校驗**：內建 `SrtCompleteness` 邏輯，自動驗證翻譯後的條目數是否與原文一致，防止 AI 漏譯。

### 3. 架構與成本 (Cloud Efficiency)
*   **模型分級策略 (Model Tiering)**：
    *   **Core Tasks**: `gemini-2.5-flash` (ASR / 高品質翻譯)
    *   **Side Tasks**: `gemini-1.5-flash-8b` (章節、OCR、簡單處理) - **節省 ~60% 非核心成本**。
    *   **QA Tasks**: `PRO_MODEL` (保留給高品質校對迴圈使用)。
*   **效能分流**：採用 ASR (2x) 與 Post-Proc (4x) 分級並行，優化 I/O 與 CPU 資源利用。

---

## 完整流程圖 (System Flowchart)

```
影片放入 input/
       │
       ▼
┌─────────────────────────────────────────────────┐
│  環境預檢 & 16kHz 單聲道提取 (FFmpeg FFT 除噪)     │
│  (1024px 影格直取 → 節省 ~9x Token + 提升準確度) │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini Flash ASR (含 Hash-based Silence Cache) │
│  輸入：.wav + Top-50 Glossary                   │
│  回傳：Native SRT (JSON Mode)                   │
└──────────┬──────────────────┬───────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────┐  ┌───────────────────────────┐
│  智慧場景偵測截幀 │  │  Glossary 自動學習 + 排序    │
│  偵測投影片翻頁   │  │  Alphabetical Sorting      │
│  → 1024px JPEG   │  │  Memory Caching (LRU)       │
└────────┬─────────┘  └──────────────┬────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│  Gemini 多模態筆記生成 (含圖像壓縮)                │
│  逐字稿 + 場景截圖 → 繁中 CFA 重點整理            │
│  輸出：_StudyNotes.md                           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  專業翻譯管線 (動態 Token 控制 + 風格模板)         │
│  支援 --style academic | casual | exam-focused  │
│  (自動生成 .zh.srt, .bilingual.srt, .vtt)       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
       LOS 章節標記生成 & 產出用量報告 (JSONL)
```

---

## 快速開始

### 進階命令範例

```bash
# 1. 費用估算與計畫預覽 (不花錢)
./venv/bin/python3 main.py --dry-run --chapters --style exam-focused

# 2. 執行全量產線 (極簡化進度面板)
./venv/bin/python3 main.py --chapters --style academic

# 3. 啟動網頁監控看板 (預設 http://localhost:5000)
./venv/bin/python3 main.py --server

# 4. 執行單元測試
./venv/bin/pytest tests/
```

### 命令參數說明

| 參數 | 說明 |
|-----|-----|
| `--dry-run` | **新功能**：美金費用預估 + 執行計畫表格 |
| `--server` | **新功能**：啟動 Flask Web 監控看板 |
| `--quality-check` | 重啟高品質 QA 校對迴圈 |
| `--style` | 翻譯風格：`academic`, `casual`, `exam-focused` |
| `--wipe` | **強力掃除**：刪除 output/、重設日誌、清理 WAV |

---

## 輸出結構

每個產出的資料夾內現在包含更加豐富的學習資源：

```
output/{影片名稱}/
├── {名稱}.srt              # 英文原文字幕
├── {名稱}.zh.srt           # 繁中翻譯字幕
├── {名稱}.bilingual.srt    # 英中對照字幕 (Best for Learning!)
├── {名稱}.vtt              # WebVTT 網頁標準格式
├── {名稱}_StudyNotes.md    # 多模態圖文筆記 (1024px)
└── {名稱}_Chapters.txt     # 自動偵測章節 (LITE Model 產出)
```

---

## 技術棧

- **AI**: Gemini 2.5 Flash / 1.5 Flash-8b (Tiered Usage)
- **UI**: Rich (Console API)
- **Web**: Flask (Minimal Dashboard)
- **Engine**: Concurrent Futures / Threading
- **Testing**: Pytest

---

## 🛠️ 歷史優化日誌 (History of Optimizations)

### Phase 3: Enterprise Reliability (2026-03)
- **Rich TUI**: 導入專業進度條與 CLI 表格。
- **Model Tiering**: 區分 Flash 與 Flash-8b 任務，節省費用。
- **Bilingual & WebVTT**: 自動雙語合稿與瀏覽器格式支援。
- **Web Dashboard**: 透過 Flask 提供視覺化任務執行看板。

### Phase 2: AI Prompt & Performance (2026-03)
- **ASR 術語精簡**: 只傳入 Top-50 關鍵術語，避免 ASR 重影或錯位。
- **風格模板系統**: 支援 academic, casual, exam-focused 三種語境。
- **智慧快取**: 實作了基於檔案 Hash 的靜音偵測快取。

### Phase 1: Foundation & Stability (2026-03)
- **Gemini Client Singleton**: 解決執行時不斷重複連線的問題。
- **JSONL 日誌系統**: 提升高並發後的 I/O 寫入穩定性。
- **自動清理邏輯**: 確保完成後自動刪除臨時 WAV 音檔。

---

### Phase 4: Intelligence & Robustness (2026-03)
- **環境預檢 (Startup Guard)**: 啟動時自動驗證 API Key 有效性與配額，防止執行中斷。
- **語言自動偵測 (Auto-Lang)**: 若未指定語言，Gemini 會自動聽 30s 樣本並推斷語種。
- **YAML 設定外置**: 新增 `settings.yaml`，無需修改代碼即可調整模型、並發數與批次大小。
- **時間軸重疊修正**: 實作 `normalize_srt` 自動修復 AI 生成的 timestamp 重疊問題，確保播放穩定。
- **Glossary 命中統計與淘汰機制**: `glossary.json` 現在會記錄術語使用次數，並支援低頻淘汰以優化 Prompt 空間。
- **批次執行摘要**: 每次 Pipeline 完成後自動生成 `run_summary_{timestamp}.md` 包含詳細費用與成果。

---

### Phase 5: Education & Ecosystem Integration (2026-03)
- **監視模式 (Watch Mode)**: 使用 `--watch` 旗號啟動，系統將持續監控 `input/` 目錄，有新影片傳入即自動觸發產線。
- **跨影片系列上下文 (Cross-Video Sync)**: 翻譯時會自動讀取同目錄下前兩部影片的學習筆記摘要，確保課程術語與邏輯的連貫性。
- **Anki 學習生態整合**: 每次執行完畢自動將術語表匯出為 `cfa_glossary.apkg`，方便學員直接導入 Anki 複習。
- **音頻品質預檢 (Quality Pre-flight)**: 產線啟動前先由 AI 評估音質，雜訊過大或失真時會主動發出警告。
- **CI/CD 自動化測試**: 整合 GitHub Actions，每次推動代碼自動執行 `pytest` 與覆蓋率檢查。
- **翻譯品質自動評分 (QA Scoring)**: 整合 「LLM-as-a-Judge」 機制，翻譯後自動由 Gemini 擔任審核官，針對術語準確度、語義流暢度進行 0-10 分評鑑並給出具體修改建議。

---

### Phase 6: Production & Smart Recovery (2026-03)
- **影片硬字幕燒錄 (Burn-in Subtitles)**: 支援 `burn_subtitles: true`，自動產出鑲嵌中英雙語字幕的影片檔，適合各種播放裝置。
- **投影片 PDF 自動生成 (Slide Deck PDF)**: 從 Vision Engine 提取的關鍵幀自動組合成一本課程投影片 PDF。
- **斷點續傳 (Partial Batch Recovery)**: 翻譯過程中若中斷，再次啟動會自動載入已完成的 batch 暫存，無需重新掃描。
- **花費預算上限 (Cost Cap)**: 可在 `settings.yaml` 設定 `max_cost_usd`，達到金額前自動暫停程式，防止超預算。
- **檔案指紋跳過 (Fingerprint Skip)**: 使用 SHA256 偵測影片內容是否變更，即便檔名相同，只要內容微調也會觸發重新處理。
- **角色分離標記 (Diarization)**: ASR 階段自動識別不同說話者（如 [Prof] / [Student]），並在字幕中標記。
- **結構化學習數據 (Structured JSON)**: 除了 Markdown 筆記，還會產出 `study_data.json`，方便串接開發 Web 自測系統。

---

### Phase 7: Robustness & Diagnostics (2026-03)
- **目錄遞迴掃描 (Recursive Search)**: 支援直接輸入大資料夾（如 `input/FI`），自動尋找底下的所有子目錄與影片檔。
- **強韌字幕解析 (Lenient SRT Parser)**: 針對 Gemini 偶發的不標準時間軸格式進行寬容解析與自動修正，大幅降低 ASR 失敗回報率。
- **進度診斷工具 (Status Checker)**: 新增 `check_status.py`，一鍵掃描 `output/` 並產生視覺化表格，快速定位處理中斷的檔案及提供續傳指令。
- **無縫斷點續傳 (Seamless Resume)**: 重啟 Pipeline 時能精準跳過已完成的階段，直接從中斷點（如翻譯）接續，不重複消耗 API 額度。

---

### Phase 8: Intelligent Diagnostic & Repair Engine (2026-03)
- **通用診斷引擎 (`recover.py`)**: 升級為強大的本地自動化修復工具。掃描 `output/` 目錄並將缺口分類為六大類型（如：有 transcript 但無 SRT、舊命名不相容、遺漏雙語字幕等）。
- **零成本修復 (Zero-cost Local Fix)**: `recover.py` 能在不呼叫任何 API（不產生費用）的情況下，自動修復本地可達成的缺漏（如 B/C/A 類缺口），大幅節省重啟產線的時間與金錢。
- **標準三步驟恢復流程**:
  1. `./venv/bin/python3 check_status.py` — 查看任務網格與具體缺口。
  2. `./venv/bin/python3 recover.py` — 自動修復所有本地可補齊的檔案。
  3. `./venv/bin/python3 main.py` — 補齊剩餘仍需 AI 運算的 ASR/翻譯/筆記部分。
- **任務網格可視化**: 提供直覺的表格顯示每部影片的詳細屬性與當前缺口，讓大規模產線管理變得輕鬆高效。

---

### Phase 10: Cost Observability & Crash-Safe Reliability (2026-03)
- **QA 評分移出翻譯熱路徑 (End-of-Run QA Summary)**: 原本每個 translation batch 都會觸發第三次 Gemini 呼叫（per-batch QA scoring），造成 API 呼叫數乘以 3 的隱性倍增。現已全面移除 per-batch 評分，改為在所有影片完成後，以 `rich.Table` 格式一次性印出本 session 新翻譯影片的品質評分（每部影片僅 1 次 API 呼叫），大幅降低翻譯成本。
- **強制中斷復原 (Crash-Safe COMPLETED Write)**: 修正進程被 SIGKILL 強制殺死時，翻譯 API 呼叫已完成但 `state.json` 未更新導致下次重跑重複消耗的問題。引擎現在在 `_dispatch_action` 返回後**立即先寫入 `COMPLETED` 狀態**，再更新輸出值。搭配 `_bootstrap_from_disk` 的磁碟檔案回填機制，確保即使在兩次寫入之間崩潰，下次啟動也能從磁碟（如 `.srt`、`.zh.srt`）補回遺失的 state 輸出，不再觸發重複 API 呼叫。
- **Notes Fallback 費用追蹤修正**: `notes_generator.py` 的多模態失敗回退 (text-only fallback) 路徑未記錄 `log_usage`，造成費用帳單低報。現已補齊 fallback 路徑的 Token 紀錄。
- **用量異常分析工具化**: 建立了按小時、按影片、按類別的 `usage_log.jsonl` 分析方法，用於定位重複執行、費用異常與 API 呼叫乘數問題。

### Phase 9: Multi-Agent Orchestration & Engine Reliability (2026-03)
- **多智能體架構 (Multi-Agent DAG Engine)**: 將原先的線性腳本 `main.py` 升級為基於 `director.py` 的有向無環圖 (DAG) 任務調度引擎。嚴格分離控制流、資訊流與狀態流。
- **配置化藍圖 (Workflow JSON Blueprint)**: 智能組件定義與依賴關係外置成 `multi_agent_workflow.json`，讓底層執行「工頭」完全按照藍圖的連線規則自動派遣工作。
- **非同步平行處理 (True DAG Concurrency)**: 支援跨影片、跨獨立任務（如 Vision 與 ASR 同步執行）的非同步並行，最大化吞吐量並大幅降低整體的批次處理時間。
- **嚴謹的型別防護 (Type Checking & Path Serialization Fix)**：解決了 `study_notes_agent` 在讀取 DAG `inputs` 時因 JSON 序列化將 `Path` 強轉為 `str` 所導致的崩潰。這類 Bug 以前會導致整個批次的影片全部中斷。目前引擎已優化為：任何 `_path` 或 `_paths` 參數在派發至 Agent 前會自動重構回 `Path` 物件，確保 `.exists()` 等檔案系統操作安全。
- **孤立分支與故障隔離 (Branch Isolation & Partial Success)**：修正了「單一 Agent 失敗導致整部影片處理死鎖」的 Bug。現在引入了 `is_blocked()` 依賴鏈檢查機制：若某個 Agent（如 `Study Notes`）失敗且重試次數耗盡，引擎僅會標記受影響的下游節點，而**與其平行的分支（如 `Chapter Agent`）將會繼續運行**。影片在部分失敗時會被標記為 `Partial` 而非整機噴發錯誤 (Branch Stalled)，最大化保留處理成果。
- **原生指數退避機制 (Bulletproof Retry Policy)**：在 `director.py` 核心深層結合 JSON 設定檔，自動套用 `max_retries`、`delay_seconds` 與 `backoff_multiplier`，完美吸收並接住任何如 API Rate Limit 的短暫異常。
- **阻斷毒化與異常向上攔截 (Exception Bubbling)**：為了確保 Retry 機制生效，移除了單一 Agent 的 Silent Failure（原先失敗時會吃下錯誤並回傳 None）。強制讓異常直接拋出由 Director 接管，避免假成功資料擴散到下游並提供正確的中斷狀態。
- **精細狀態寫入與檔案自動同步 (Disk-State Sync)**：引入了 `_bootstrap_from_disk` 機制。引擎啟動前會主動掃描磁碟上已存在的 `.srt`、`.zh.srt`、筆記與關鍵幀。即便 `state.json` 遺失或使用舊版腳本產出的檔案，新引擎也能精準識別並自動將對應 Agent 標記為 `COMPLETED`，同時回填資料以供下游任務使用，徹底杜絕重複運算與 API 浪費。
- **影片內容指紋校驗 (Video Hash Guard)**：在 `state.json` 中內嵌影片 SHA256 指紋。若偵測到同名影片但內容已變更，引擎會自動重置該影片的所有處理狀態，確保字幕、筆記與影片內容的絕對一致性。

---

## 🛠️ 2026-03-24 更新日誌 (OpenRouter 遷移)

全部完成。以下是所有修改的總結：

| 文件 | 修改內容 |
|:---|:---|
| requirements.txt | 新增 `openai` 套件 |
| settings.yaml | 新增 `openrouter.text_model` 配置 |
| config.py | 新增 `OPENROUTER_TEXT_MODEL`，翻譯提示改為簡體中文 |
| openrouter_client.py | 新建 OpenRouter 單例客戶端 |
| usage_tracker.py | `:free` 模型 cost = 0 |
| translator.py | 完全切換至 OpenRouter，移除 Gemini 依賴 |
| chapter_generator.py | 完全切換至 OpenRouter，語言改簡體中文 |
| qa_agent.py | 完全切換至 OpenRouter，語言改簡體中文 |
| notes_generator.py | 主路徑保留 Gemini（多模態/圖片），文字回退改 OpenRouter，語言改簡體中文 |

### 架構邏輯：

1. **ASR + Vision（音頻/圖片）** → 繼續使用 Gemini (多模態優勢)。
2. **Translation + Chapters + QA + Study Notes fallback** → 全部走 OpenRouter 免費模型 (節省成本)。

---

### Phase 11: Pipeline Robustness & Monolithic Recovery (2026-03)
- **單一巨大條目自動切割 (split_monolithic_entry)**：針對 ASR 偶發將整段影片誤存為單一 300KB 字幕的問題，實作了基於句子邊界的自動切割邏輯，並補充合成時間戳（估算率 ~2.2 字/秒）。
- **翻譯器 Pre-flight 防護**：translator.py 現在會在呼叫 API 前檢查是否有超過 2000 字元的異常條目，若有則自動觸發切割，徹底杜絕 400 Context Length Error。
- **後 ASR 密度驗證**：asr_engine.py 新增檢查點，若長影片產出的字幕密度過低（如每 2 分鐘少於 1 條），將自動發出警告並記錄 Fail，防止損毀資料進入管線。
- **SRT 修復工具升級**：recover.py 現在具備 D_monolithic 類別偵測，可一鍵修復所有本地已損毀的「一條龍」字幕。

---

## 🛠️ 2026-03-28 異常修復摘要 (Monolithic SRT Fix)

### 立即修復項目 (Hotfix)
- **檔案**: output/2026-l1-et-lm5-video/2026-l1-et-lm5-video.srt
- **狀況**: 原始 ASR 產出僅 1 條字幕 (310KB)，導致翻譯卡死。
- **修復後**: 3406 條字幕，格式正確，句子邊界切割。
- **備份**: 原始損毀檔已更名為 .srt.bak。
- **後續**: 可直接重新執行 main.py 進行翻譯。

### 三層防護機制策略 (Defense in Depth)
| 位置 | 策略 | 效果 |
| :--- | :--- | :--- |
| **srt_utils.py** | split_monolithic_entry() | 拆解巨型條目並補強合成時間戳。 |
| **recover.py** | D_monolithic 偵測 | 自動發現並修補所有損毀的 ASR 檔案。 |
| **translator.py** | Pre-flight 2k-char Guard | 翻譯前自動攔截並拆解超大條目。 |
| **asr_engine.py** | Density Verification | 第一時間攔截 ASR 異常，確保資料品質。 |

---

### 🐛 已修復的引擎 Bug (Engine Bug Fixes)

#### Bug 1：無限重試迴圈（最嚴重）
- **位置**: `director.py:285`
- **原因**: `ready_agents` 原本只排除 `completed_agents`，但 `FAILED` 的 agent 不在其中。這導致在同一次 session 內，失敗任務（如 ET-LM5）會被不斷重新派發，陷入「失敗 -> 立即重試 -> 再失敗」的無限迴圈，直到被手動 kill。
- **修復**: 在 `ready_agents` 判斷中加入 `a.id not in failed_agents`。一旦某個 agent 在本次執行中失敗，同次 session 內將不再重試，確保流程能繼續向下走。

#### Bug 2：永久失敗 vs 暫時失敗沒有區分
- **位置**: `director.py:356 / director.py:33`
- **修復**: 引入了 `FAILED_PERMANENT` 狀態與 `_is_permanent_error` 判斷：
    - **400 / Context Length / Payload Too Large**: 標記為 `FAILED_PERMANENT`，系統偵測到這類「重試也沒用」的錯誤時會自動停止該任務，不再浪費 Token。
    - **429 / 503 / 網路逾時**: 標記為 `FAILED`，下次運行時會自動重試。

#### Bug 3：跨 session 的 FAILED_PERMANENT 自動解鎖
- **位置**: `director.py:174`
- **修復**: 在 `_bootstrap_from_disk` 階段新增邏輯。當 `recover.py` 修復了 SRT 並生成了 `.srt.bak` 時，引擎會自動將對應的 `FAILED_PERMANENT` 狀態重設為 `PENDING`。這使得修復後的影片在下次跑 `main.py` 時能自動獲得翻譯機會，無需手動修改 `state.json`。
