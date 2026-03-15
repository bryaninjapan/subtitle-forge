# Subtitle Forge

CFA 教學影片自動化處理工具，透過 Gemini API 完成語音辨識、中文字幕翻譯、學習筆記生成。

---

## 核心優化功能

本專案已針對大規模批次處理進行了深度優化，具備工業級的穩定性與產出品質：

### 1. 智慧管線與穩定性
*   **啟動預檢 (Pre-flight Check)**：自動檢查 `ffmpeg` 與 `ffprobe` 環境，確保工具就緒。
*   **斷點續傳 (Checkpointing)**：自動跳過已完成的 ASR、翻譯或筆記生成步驟，支援中斷後無縫恢復。
*   **雙重並發 (Dual-Pool Concurrency)**：分離 ASR 運算與後處理（翻譯/筆記），極大化 GPU/API 吞吐量。
*   **失敗回退 (Fallback)**：多模態筆記生成失敗時自動重試「純文字模式」，確保任務不中斷。

### 2. 高品質產出
*   **術語感知 ASR (Glossary-Aware)**：轉錄時主動參考 `glossary.json`，精準識別 CFA 專有名詞。
*   **智慧場景偵測 (Scene-Change Detection)**：改用 FFmpeg 偵測畫面變動（如投影片翻頁）擷取畫面，不再有冗餘截圖。
*   **跨批次語境翻譯 (Contextual Translation)**：翻譯時參考前一區塊的語境，解決分段翻譯導致的口吻不連貫。
*   **SRT 自動修復 (Normalization)**：自動校正時間軸、序號與標點格式，確保播放器 100% 相容。

### 3. 資源效率
*   **自動清理 (Auto-Cleanup)**：任務完成後自動刪除巨大的臨時音檔 (`.wav`)，節省 90% 以上磁碟空間。
*   **音訊優先 ASR**：僅上傳 16kHz WAV 到 Gemini，較上傳影片節省約 9 倍 Token 消耗。

---

## 完整流程圖

```
影片放入 input/
       │
       ▼
┌─────────────────────────────────────────────────┐
│  環境預檢 (ffmpeg/ffprobe Verify)                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  ffmpeg 提取音訊 (WAV 16kHz)                     │
│  (節省 ~90% token，資源清理機制保護)              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini ASR + Glossary 輔助                      │
│  輸入：.wav + glossary.json                      │
│  輸出：video.srt + video.txt                    │
└──────────┬──────────────────┬───────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────┐  ┌───────────────────────────┐
│  智慧場景偵測截幀 │  │  Glossary 自動學習          │
│  偵測投影片翻頁   │  │  從逐字稿抓取新術語         │
│  → frames/       │  │  防止併發寫入衝突           │
└────────┬─────────┘  └──────────────┬────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│  Gemini 多模態筆記生成 (備有 Text-only Fallback)  │
│  逐字稿 + 場景截圖 → 繁中 CFA 重點整理           │
│  輸出：_StudyNotes.md                           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  跨語境批次翻譯 (.zh.srt)                        │
│  Batch N + Batch N-1 Context                    │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
       清理暫存檔 & 產出 Dashboard 統計
```

---

## 輸出結構

```
output/
└── {影片名稱}/
    ├── {影片名稱}.srt               ← 原文字幕（帶時間軸，已 Normalization）
    ├── {影片名稱}.txt               ← 純文字逐字稿
    ├── {影片名稱}.zh.srt            ← 繁體中文字幕（具語境連貫性）
    ├── {影片名稱}_StudyNotes.md     ← CFA 學習筆記（結合影像分析）
    └── frames/
        ├── frame_001.jpg            ← 智慧偵測到的場景變換畫面
        └── ...
```

---

## 環境需求

- Python 3.10+
- **ffmpeg & ffprobe**（`brew install ffmpeg`）
- Gemini API Key（`export GEMINI_API_KEY=your_key`）

---

## 安裝

```bash
git clone https://github.com/your-repo/subtitle-forge.git
cd subtitle-forge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 使用方式

### 基本命令

```bash
# 處理所有影片（自動檢查斷點、自動清理）
python main.py

# 指定輸入
python main.py --input video.mp4

# 跳過視覺分析（純文字處理）
python main.py --no-vision
```

---

## 術語表管理 (glossary.json)

翻譯與 ASR 引擎共享的知識庫。
- **寫鎖保護**：支援多影片同時更新術語表而不損毀檔案。
- **手動同步**：`python main.py --update-glossary`。

---

## 技術棧

| 功能 | 工具 |
|-----|-----|
| AI 引擎 | Google Gemini API (`gemini-2.5-flash`) |
| 影音處理 | FFmpeg (Scene detection, Audio Extract) |
| 並發架構 | `ThreadPoolExecutor` (ASR & Post-proc 雙池) |
| 穩定性 | Exponential Backoff Retries, Checkpointing |

---

## 專案結構

- `main.py`: 核心調度，具備音檔清理與斷點邏輯。
- `asr_engine.py`: 術語感知的轉錄引擎。
- `vision_engine.py`: 基於場景變動的智慧截圖系統。
- `notes_generator.py`: 多模態/純文本回退筆記生成。
- `translator.py`: 支援跨批次語境參考的翻譯器。
- `srt_utils.py`: SRT 解析與工業級 Normalization 工具。
- `usage_tracker.py`: 自動產生專案總結 Dashboard。
ython 3.10+
- ffmpeg（`brew install ffmpeg`）
- Gemini API Key（`export GEMINI_API_KEY=your_key`）

---

## 安裝

```bash
cd subtitle-forge
source venv/bin/activate
pip install -r requirements.txt
```

---

## 使用方式

### 完整流程（最常用）

```bash
# 把影片放入 input/，執行完整流程
python main.py

# 指定單一影片
python main.py --input input/video.mp4

# 指定資料夾
python main.py --input /path/to/videos/

# 指定語言（預設自動偵測）
python main.py --language English
```

### 分階段執行

```bash
# 只做語音辨識（輸出 .srt + .txt）
python main.py --asr-only

# 只做翻譯（需已有 .srt）
python main.py --translate-only

# 只生成學習筆記（需已有 .txt）
python main.py --notes-only

# 只更新術語表
python main.py --update-glossary

# 跳過截幀（加快 notes 生成）
python main.py --notes-only --no-vision
```

### 防止電腦睡眠（長時間處理）

```bash
# 用 caffeinate 包住指令，確保不中途睡眠
caffeinate -dis python main.py
caffeinate -dis bash process_fs_batch.sh
```

---

## 術語表 (glossary.json)

翻譯時自動參考 `glossary.json` 裡的 CFA 術語對照，確保一致性。

- **自動更新**：每次翻譯前 Gemini 會掃描逐字稿，將新發現的術語加入
- **手動觸發**：`python main.py --update-glossary`（掃描所有已有的 .srt 檔案）

---

## Token 消耗估算

| 影片長度 | ASR（音訊上傳） | 翻譯 | 學習筆記 | 總估算成本 |
|---------|--------------|-----|---------|----------|
| 30 分鐘  | ~58K tokens  | ~20K tokens | ~50K tokens | ~$0.03 |
| 45 分鐘  | ~86K tokens  | ~30K tokens | ~55K tokens | ~$0.04 |
| 75 分鐘  | ~144K tokens | ~50K tokens | ~60K tokens | ~$0.06 |

> 音訊模式（現行）：~1,920 token/min。若直接上傳影片則 ~17,700 token/min（9 倍）。

---

## 技術棧

| 功能 | 工具 |
|-----|-----|
| ASR / 翻譯 / 筆記 | Google Gemini API (`gemini-2.5-flash`) |
| 音訊提取 / 截幀 | ffmpeg |
| 並發處理 | Python `ThreadPoolExecutor` |
| 字幕格式 | SRT |

---

## 專案結構

```
subtitle-forge/
├── main.py              # CLI 入口，流程協調
├── config.py            # 模型名稱、並發數、路徑設定
├── asr_engine.py        # 音訊提取 + Gemini ASR
├── translator.py        # 批次翻譯 + 並發控制
├── notes_generator.py   # CFA 學習筆記生成
├── vision_engine.py     # 關鍵幀截取
├── glossary_manager.py  # 術語自動學習
├── srt_utils.py         # SRT 解析 / 格式化工具
├── usage_tracker.py     # Token 用量記錄
├── glossary.json        # CFA 術語對照表
├── pipeline_report.md   # 使用量報告（自動更新）
├── input/               # 放入待處理影片
└── output/              # 輸出結果
```
