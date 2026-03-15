# Subtitle Forge

CFA 教學影片自動化處理工具，透過 Gemini API 完成語音辨識、中文字幕翻譯、學習筆記生成與 LOS 章節標記。

---

## 核心優化功能

本專案已針對大規模批次處理進行了深度優化，具備工業級的穩定性與產出品質：

### 1. 智慧管線與穩定性 (Enterprise Stability)
*   **啟動預導 (Pre-flight Check)**：自動檢查 `ffmpeg` 環境，避免運行中崩潰。
*   **自適應併發縮放 (Adaptive Rate Limiting)**：具備全局 **Exponential Backoff** 機制，當偵測到 API 頻率限制 (429) 時，所有執行緒會同步進入冷卻暫停。
*   **斷點續傳 (Checkpointing)**：自動跳過已完成的 ASR、翻譯或筆記生成，支援隨時中斷重啟。
*   **原子化日誌 (Atomic Logging)**：採用寫鎖保護機制，確保多執行緒環境下 `usage_log.json` 與 `glossary.json` 不損毀。

### 2. 高品質產出 (Flash Power Features)
*   **原生系統指令 (Native System Instructions)**：利用 Gemini Flash 特性將指令與數據分離，大幅提升指令遵循度。
*   **JSON 回傳模式 (JSON Response Mode)**：翻譯引擎強制採用 JSON 格式輸出，杜絕正則表達式解析失敗的風險。
*   **術語感知 ASR (Glossary-Aware)**：轉錄時主動參考 `glossary.json`，精準識別 CFA 專有名詞。
*   **跨批次語境翻譯 (Contextual Translation)**：翻譯時參考前一區塊的語境，解決分段翻譯導致的口吻不連貫。

### 3. 資源效率與智慧分析
*   **靜音啟發式過濾 (Silence Heuristic Filter)**：自動偵測音檔靜音比例，若高於 95% 則自動跳過 API，節省 Token 成本。
*   **自動 LOS 章節生成 (Auto Chaptering)**：分析逐字稿偵測 **Learning Outcome Statements (LOS)** 切換點，產出播放器相容的章節清單。
*   **智慧標頭過濾 (Normalization)**：自動修正 SRT 格式錯誤、重複序號與非法字符。

---

## 完整流程圖

```
影片放入 input/
       │
       ▼
┌─────────────────────────────────────────────────┐
│  環境預檢 & 音訊提取 (FFmpeg FFT 除噪 + 標準化)    │
│  (16kHz 單聲道，節省 ~9x Token + 提升準確度)      │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini Flash ASR (含 Silence Filter)           │
│  輸入：.wav + Glossary                          │
│  回傳：Native SRT (JSON Mode)                   │
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
│  Gemini 多模態筆記生成 (含專業風格定製)           │
│  逐字稿 + 場景截圖 → 繁中 CFA 重點整理            │
│  輸出：_StudyNotes.md                           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  專業翻譯管線 (Batch N + N-1 Context)            │
│  支援 --style academic | casual | exam-focused  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
       LOS 章節標記生成 & 產出用量報告
```

---

## 輸出結構

```
output/
└── {影片名稱}/
    ├── {影片名稱}.srt               ← 原文字幕（已校準時間軸）
    ├── {影片名稱}.txt               ← 純文字逐字稿
    ├── {影片名稱}.zh.srt            ← 繁體中文字幕（具風格定製）
    ├── {影片名稱}_StudyNotes.md     ← CFA 學習筆記（結合影像分析）
    ├── {影片名稱}_Chapters.txt      ← 自動偵測的 LOS 章節清單
    └── frames/
        ├── frame_001.jpg            ← 投影片翻頁關鍵幀
        └── ...
```

---

## 使用方式

### 基本命令

```bash
# 完整自動流程 (ASR + 翻譯 + 筆記 + 章節)
python main.py --chapters --style exam-focused

# 只做維護操作
python main.py --update-glossary  # 全局術語學習
python main.py --cleanup         # 清除暫存 .wav 檔
```

### 命令參數說明

| 參數 | 說明 |
|-----|-----|
| `--input` | 指定影片路徑或資料夾 |
| `--language` | 強制來源語系（預設自動偵測） |
| `--style` | 翻譯風格：`academic` (學術), `casual` (口語), `exam-focused` (應考型) |
| `--chapters` | 開啟自動 LOS 章節標記生成 |
| `--no-vision` | 禁用畫面分析，僅處理音訊與文字 |

---

## 環境需求

- Python 3.10+
- **FFmpeg** (需支援 `afftdn`, `loudnorm`, `silencedetect` 濾波器)
- Gemini API Key (建議使用 Gemini Flash 1.5 或 2.0 模型)

---

## 技術架構

- **AI Model**: Google Gemini Flash (System Instruction + JSON Mode)
- **Engine**: Python 3.10 + Concurrent Threading
- **Audio Processing**: FFmpeg High-Fidelity Filtering
- **Storage**: JSON-based state tracking & atomic logging
