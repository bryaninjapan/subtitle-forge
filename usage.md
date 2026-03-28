

# 📘 Subtitle Forge 使用手冊 (User Manual)

## 🧭 核心引擎: Multi-Agent Director (2026 最新整合)
專案已全面升級為**多智能體有向無環圖 (DAG) 協作架構**。
目前的 `main.py` 已重構為統一入口，內部調度強大的 `director.py` 引擎，不僅保留了原有的進階功能（如 Watcher、Cost Tracking），更引入了強大的重試與並行機制：

```bash
./venv/bin/python3 main.py input/FI/ --language English --style academic
```
**底層安全與防護機制：**
1. **精準重播與自癒**: 每支影片會生成專屬的 `state.json`。若執行失敗，您只需要**原封不動重新執行主程式**。系統會精準從中斷點喚醒尚未完成的 Agent，不再重複消耗 API 費用。
2. **強制中斷復原 (Crash-Safe COMPLETED Write)**: Agent 執行成功後，引擎**先寫入 `COMPLETED` 狀態再更新輸出**。若進程在兩者之間被強制殺死 (SIGKILL)，下次啟動時 `state.json` 已有 COMPLETED 標記，`_bootstrap_from_disk` 再從磁碟上現有的 `.srt` 等檔案補回遺失的輸出值，確保 Agent 不會被重複執行。
3. **自動退避重試**: 內建原生 Retry Policy，遇到 Gemini API 速率限制 (Rate limit) 等短暫錯誤會自動等待並指數退避重試，無需人工干預。
4. **磁碟檔案同步 (Disk-State Sync)**: 引擎會自動掃描 `output/` 目錄下的現有成果（如 `.srt`, `.zh.srt`）。即便 `state.json` 不存在，引擎也會自動標記已完成項目，杜絕重複運算與 API 浪費。
5. **內容指紋校驗 (Video Hash Guard)**: 自動校驗影片 SHA256。若偵測到同名但內容已變更的影片，引擎會自動重置狀態重新處理，防止字幕與內容不匹配。
6. **錯誤隔離與斷點**: 單一影片或單一任務分支失敗，不會導致整個批次崩潰，且支援隨時暫停後重啟。

## 1. ⚙️ 全域配置 (settings.yaml)
這是產線的「大腦」，你可以透過更改此檔案控制自動化行為。

| 配置項 | 建議值 | 說明 |
|:--- |:--- |:--- |
| **`max_cost_usd`** | `5.0` | **錢包守護者**。累積花費超過此金額時，程式會安全跳回並停止。 |
| **`burn_subtitles`** | `true` | **生產力核心**。翻譯後自動將中英字幕燒錄進影片（產出 `.burned.mp4`）。 |
| **`use_qa_scoring`** | `false` | **品質保證**。已從翻譯熱路徑移除。現在改為在所有影片完成後，於 terminal 一次性印出 QA 評分摘要表（僅針對本次 session 新翻譯的影片）。 |
| **`use_context_caching`** | `false` | **大型任務加速**。當術語表極大時開啟，可省下重複傳送 Token 的費用。 |
| **`slide_pdf`** | `true` | **學習輔助**。從 Vision Engine 提取圖幀，並自動組合成一本講義 PDF。 |
| **`structured_json`** | `true` | **數據擴展**。產出 `study_data.json` 供 App 自行開發練習題使用。 |

---

## 2. ⌨️ 指令參數詳解 (CLI Options)

### 處理型參數 (指令執行功能)
*   **`paths`** (舊版 `--input`): 直接傳入輸入路徑。可以是單一檔案、多個檔案，或整個資料夾（**自動遞迴掃描所有子目錄**）。
    *   範例: `./venv/bin/python3 main.py input/FI/`
*   **`--language, -l`**: **影片原文語言提示**。告訴 AI 影片裡的人在說什麼，提高識別率。
    *   若省略則啟動 **AI 自動偵測 (Auto-Detect)**。
*   **`--chapters`**: **生成標記點**。根據內容產出 YouTube 格式的 Timecode 章節資訊。
*   **`--style`**: **翻譯風格**。預設為 `academic`（學術），可選 `casual`（口語）或 `exam-focused`（強調考點概念）。
*   **`--no-vision`**: **關閉視覺分析**。不截圖、不產出 PDF，僅處理 ASR 字幕與翻譯。

### 系統型參數 (控制程式運行)
*   **`--watch`**: **啟動監視模式**。監視 `input/` 資料夾，隨丟隨跑，無需手動重啟。
*   **`--dry-run`**: **模擬模式**。估算花費與列出待處理清單，**不消耗 Token 費用**。
*   **`--server`**: **啟動 Web 介面模式**。開啟一個本機伺服器 (Port 5000) 供瀏覽器操作。
*   **`--wipe`**: **磁碟空間清理**。強制刪除 `output/` 目錄下所有內容，用於重啟乾淨的環境。

---

## 3. 🎯 四大核心使用場景 (Scenarios)

### 場景 A：全自動學習工廠 (推薦)
想讓後台自動處理剛錄製好的課程：
1.  在 `settings.yaml` 設定 `burn_subtitles: true` 與 `slide_pdf: true`。
2.  執行指令：`./venv/bin/python3 main.py --watch --chapters`
3.  **結果**: 丟入影片後，自動得到：`燒錄影片` + `SRT` + `筆記` + `PDF` + `Anki 牌組`。

### 場景 B：極致品質與精準度
正在處理難度極高的衍生性商品或財報分析課程：
1.  在 `settings.yaml` 設定 `use_qa_loop: true`。
2.  這會啟動「翻譯 -> 二次 Glossary 術語校對」的二階段審核流程。
3.  QA 評分（0-10 分）會在**所有影片全部完成後**自動在 terminal 印出摘要表，不再佔用翻譯 API 配額。

### 場景 C：大型影片系列 (加速方案)
一次處理 20 部、每部 2 小時的長系列影片：
1.  在 `settings.yaml` 設定 `use_context_caching: true`。
2.  這會將你的 CFA 術語字典暫存在雲端，確保後續批次請求更便宜且反應更快。

### 場景 D：環境整理
實驗一陣子後 `output/` 目錄太亂，想重新來過：
執行 `./venv/bin/python3 main.py --wipe`。

### 場景 E：中斷續傳與錯誤診斷
處理大量影片時途中關閉或遇到斷線，執行**三步驟標準流程**：

```
Step 1: ./venv/bin/python3 check_status.py     ← 查看任務網格，了解哪些影片缺什麼
Step 2: ./venv/bin/python3 recover.py          ← 自動修復舊版遺留的所有本地可修缺口（零 API 費用）
Step 3: ./venv/bin/python3 main.py input/      ← 透過多智能體架構自動補齊仍需 API 的部分```

`recover.py` 會自動掃描 `output/` 下的每個目錄，將缺口分成六類：

| 類型 | 條件 | 是否需要 API |
|:---|:---|:---:|
| B — 重新解析 transcript | 有 `transcript.txt`（含 SRT）但無 `.srt` | 否 |
| C — 舊命名修正 | 有 `subtitle.srt` 但無 `{stem}.srt` | 否 |
| A — 補 bilingual | 有 `.srt` + `.zh.srt` 但無 `.bilingual.srt` | 否 |
| Translation | 有 `.srt` 但無 `.zh.srt` | 是 |
| ASR | 無 `.srt` 且無可解析 transcript | 是 |
| Study Notes | 翻譯完整但無 `.studynotes.md` | 是 |

執行後會顯示任務網格、修復進度，並印出「仍需 API」的影片清單與建議指令。

---

## 📊 監控日誌
*   **`usage_log.jsonl`**: 每次 API 呼叫的原始數據（類別、影片名稱、input/output tokens、費用）。
*   **`cost_history.md`**: 每次執行的費用彙總歷史記錄。
*   **`cfa_glossary.apkg`**: 每次執行完自動在根目錄產生的 Anki 匯入檔。
*   **QA 評分摘要表**: 每次 session 完成後，在 Financial Summary 前自動印出本次新翻譯影片的 0-10 評分與建議（僅限新翻譯，不對已完成的影片重新評分）。

---

## 🛠️ 開發與 AI 智能體擴展建議 (Developer Notes)
如果您計畫開發新的 Agent 或使用 AI 協助修改產線，請務必遵守以下 **Path Serialization (路徑序列化)** 規則，以防止產線因型別錯誤而崩潰：

### 核心限制：JSON 不支援 `Path` 物件
`director.py` 的 `StateStore` 為了持久化進度，會將所有輸出轉換為 JSON。這意味著所有 `pathlib.Path` 物件在存入 `state.json` 時都會自動變成 **`str` (字串)**。

### 修復模式：手動還原型別
當您的 Agent 從 `inputs` 讀取資料並需要調用檔案系統方法（如 `.exists()` 或 `.mkdir()`）時，**務必將字串重新包裝回 Path 物件**：

*   **單一路徑**：`Path(inputs["some_path"])`
*   **路徑列表**：`[Path(p) for p in inputs["frame_paths"]]`

此慣例已整合於現有 Agent 的派發邏輯中，未來擴充功能時請保持一致，以確保系統的型別安全與執行穩定性。

---

## 🚀 批次處理最佳實務 (Batch Processing Best Practices)
為了最大化多智能體引擎的效能並避免不同批次的任務混淆，執行大規模產線時請遵循以下建議清單：

1. **明確指定路徑**：盡量指定具體的資料夾（如 `./venv/bin/python3 main.py input/EQ/`），而非直接下達 `main.py --language English`。這能防止引擎同時掃描整個 `input/` 目錄，導致不同批次的影片任務夾雜。
2. **先修復、後調度**：在啟動 `main.py` 大規模調度 AI 前，建議先執行一次 `recover.py`。這能先以「零 API 花費」的方式修復本地可修復的記錄（如同步舊的 SRT），減輕 ASR Agent 的負擔。
3. **故障隔離機制**：現在系統已具備 **孤立分支保護 (Branch Isolation)**。若某個 Agent（如 Study Notes）因特殊原因失敗，**不會再阻塞與其平行的分支（如 Chapter Agent）**。您可以放心讓長期任務在後台運行，系統會盡可能保留所有成功的「Partial Success」成果，待您手動修復特定錯誤後再續傳。

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

1. **ASR + Vision（音頻/圖片）** → 繼續使用 Gemini。
2. **Translation + Chapters + QA + Study Notes fallback** → 全部走 OpenRouter 免費模型。
