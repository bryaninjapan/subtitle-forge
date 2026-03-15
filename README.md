# Subtitle Forge

CFA 教學影片自動化處理工具，透過 Gemini API 完成語音辨識、中文字幕翻譯、學習筆記生成。

---

## 它在做什麼

把影片丟進去，自動幫你：
1. **提取音訊** → 轉成 WAV（省 token，不上傳整個影片）
2. **語音辨識** → 上傳到 Gemini，生成帶時間軸的英文字幕 (.srt) 和純文字稿 (.txt)
3. **截取投影片** → 每 5 分鐘截一張關鍵畫面
4. **生成學習筆記** → 根據逐字稿產出繁體中文 CFA 重點整理 (.md)
5. **翻譯字幕** → 批次送 Gemini 翻譯，輸出繁體中文字幕 (.zh.srt)

---

## 完整流程圖

```
影片放入 input/
       │
       ▼
┌─────────────────────────────────────────────────┐
│  ffmpeg 提取音訊                                 │
│  video.mp4  →  video.wav                        │
│  (節省 ~90% token，從 17K/min 降到 2K/min)       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini ASR（語音辨識）                          │
│  上傳 .wav → 取得逐字稿                          │
│  輸出：video.srt  +  video.txt                  │
└──────────┬──────────────────┬───────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────┐  ┌───────────────────────────┐
│  ffmpeg 截幀     │  │  Glossary 術語掃描          │
│  每 5 分鐘一張   │  │  從逐字稿找新的 CFA 術語    │
│  → frames/       │  │  自動更新 glossary.json     │
└────────┬─────────┘  └──────────────┬────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────────┐
│  Gemini 生成學習筆記                             │
│  逐字稿 + 投影片截圖 → 繁中 CFA 重點整理         │
│  輸出：video_StudyNotes.md                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Gemini 批次翻譯字幕                             │
│  每批 50 條，最多 5 個並發請求                   │
│  輸出：video.zh.srt                              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
             output/ 輸出完成
```

### 多影片並行策略

一次處理多部影片時，流程會交錯執行以節省時間：

```
影片 1: [──ASR──][──Notes──] → [翻譯等待中]
影片 2:          [──ASR──][──Notes──] → [翻譯等待中]
影片 3:                   [──ASR──][──Notes──] → [翻譯]
                                                  ↓
                                          [翻譯 1][翻譯 2][翻譯 3]
```

同時最多 **2 部影片** 並行跑 ASR，翻譯由單一 worker 依序執行。

---

## 輸出結構

```
output/
└── {影片名稱}/
    ├── {影片名稱}.wav               ← 提取的音訊（快取，重跑不重傳）
    ├── {影片名稱}.srt               ← 原文字幕（帶時間軸）
    ├── {影片名稱}.txt               ← 純文字逐字稿
    ├── {影片名稱}.zh.srt            ← 繁體中文字幕
    ├── {影片名稱}_StudyNotes.md     ← CFA 學習筆記
    └── frames/
        ├── frame_001.jpg            ← 投影片截圖（每 5 分鐘）
        ├── frame_002.jpg
        └── ...
```

---

## 環境需求

- Python 3.10+
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
