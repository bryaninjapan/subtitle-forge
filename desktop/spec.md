# Subtitle Forge — React Frontend Specification

## 架構

6 個頁面 + 側邊導航，所有頁面透過 HTTP call `localhost:5000`。

```
desktop/src/
├── api.ts                  # API 封裝層
├── types.ts                # TypeScript 型別
├── App.tsx                 # 側邊導航 + 頁面路由
├── main.tsx                # React 入口
│
├── pages/
│   ├── AudioFile.tsx       # 頁面 1: 音檔轉字幕
│   ├── Batch.tsx           # 頁面 2: 批次辨識
│   ├── Record.tsx          # 頁面 3: 錄製轉換
│   ├── Endpoint.tsx        # 頁面 4: 端點服務
│   ├── ModelManage.tsx     # 頁面 5: 模型與裝置
│   └── Settings.tsx        # 頁面 6: 設定
│
└── styles/
    └── global.css          # 暗色主題
```

## 頁面規格

### P1: 音檔轉字幕 (AudioFile.tsx)

單一音檔上傳、轉錄、檢視結果：

```
┌─ 上傳區 ──────────────────────────────────────┐
│  夏天這一站.mp3  (3.1 MB)           [×]       │ ← 選檔後顯示檔名
│  [選擇檔案]                                      │ ← 未選檔時顯示
└────────────────────────────────────────────────┘

[▶ 開始轉換]  [📂 輸出資料夾]  [💾 字幕存檔]     ← 按鈕列

語言: [自動 ▼]   說話者分離: [○]   人數: [自動 ▼]
時間軸對齊: [●]

辨識提示（可選）
┌──────────────────────────────────────────────┐
│  貼入歌詞、關鍵字或背景說明...                  │
│                               [讀入TXT...]    │
└──────────────────────────────────────────────┘

████████████████████░░░░  完成  100%            ← 進度條

┌── 辨識結果 ──────────────────────────────────┐
│  [=====波形=====]        01:10                │
│  週末 窗外 花 黃 有 別 我 每                  │ ← 字詞區塊
│  [▶] [■] [🎤]  點波形/字幕可跳播              │ ← 播放控制
└──────────────────────────────────────────────┘

00:01 → 00:03   週末的早晨                         ← 字幕列表
00:03 → 00:05   睡到自然醒
```

**States**:
- 未上傳: 顯示「選擇檔案」按鈕
- 已上傳: 顯示檔名 + 檔案大小 + [×] 移除
- 轉換中: 按鈕列置灰，進度條動畫
- 完成: 顯示波形 + 字詞區塊 + 字幕列表

**API calls**:
- `POST /upload` (上傳檔案)
- `GET /progress` (輪詢進度)
- `GET /outputs/:name/:file` (下載字幕)

---

### P2: 批次辨識 (Batch.tsx)

多檔批次處理：

```
批次辨識

[＋ 加入檔案]  [▶ 全部開始]  說話者分離: [○]  人數: [自動 ▼]   0 / 3 完成

夏天這一站.mp3      ████████████░░░░  60%  轉換中  [⋮]
月宮・換裝夢遊.mp3   ░░░░░░░░░░░░░░   0%  待處理  [⋮]
華裳夢遊.mp3        ░░░░░░░░░░░░░░   0%  待處理  [⋮]
```

**States**:
- 無檔案: 空列表 + 「加入檔案」按鈕
- 佇列中: 顯示進度條 + 狀態標籤 (待處理/轉換中/完成/失敗)
- 全部完成: 按鈕變成「全部清除」

**API calls**:
- `POST /upload` (每個檔案)
- `GET /progress` (輪詢所有 task)
- `POST /cancel/:id` (取消單一任務)

---

### P3: 錄製轉換 (Record.tsx)

即時麥克風錄音轉文字：

```
錄製轉換

麥克風: [預設麥克風 ▼]  [重新整理]  語言: [自動 ▼]

┌──────────────────────────────────────┐
│                                      │
│           [ 🎤 ]                     │ ← 大圓形按鈕
│            00:00                     │
│                                      │
│  錄製轉換：偵測到說話停頓時才辨識...    │
└──────────────────────────────────────┘

即時字幕
即時存檔: [○]          [清除]  [儲存字幕]

┌──────────────────────────────────────┐
│  開始錄音後，辨識結果會逐段出現...      │
└──────────────────────────────────────┘
```

**States**:
- 未開始: 顯示大麥克風按鈕 + 說明文字
- 錄音中: 按鈕變紅色脈動，計時器跑
- 暫停: 保留已辨識文字

**API**: 即時錄音不走 HTTP，需用 MediaRecorder + WebSocket 或 file upload。

---

### P4: 端點服務 (Endpoint.tsx)

讓手機或其他裝置上傳音檔：

```
OpenAI 相容轉錄服務

[●] 啟動服務

上傳網頁                    存取金鑰
┌──────────────────┐        ┌────────┐
│ [QR Code]        │        │ ●●●●●● │
│ http://192.168.. │        │[顯示]   │
│ [複製]           │        │[重設]   │
└──────────────────┘        └────────┘

對外臨時網址 (Cloudflare)
[○] 對外   ⚠️ 網址含金鑰，用完請關閉
```

**States**:
- 未啟動: 灰色 toggle，無 QR code
- 啟動: 顯示 QR code + URL + key
- 對外啟用: Cloudflare tunnel

**API calls**:
- `POST /endpoint/start` (啟動服務)
- `POST /endpoint/stop` (停止)
- `GET /endpoint/status` (取得 URL + QR code data)

---

### P5: 模型與裝置 (ModelManage.tsx)

顯示各 ASR backend 的模型下載狀態：

```
系統自檢  核心就緒 · 1 項將於啟用時自動下載  [重新檢查]

Qwen · OpenVINO (CPU)
  ASR 模型 (0.6B)     ● 已下載
  語音分段 VAD         ● 已內建
  時間軸對齊 FA        ● 已下載
  說話者分離           ● 已下載

CRISPASR (Vulkan)
  CrispASR 核心        ● 使用中
  Whisper 模型 (Q4)    ○ 未下載 (啟用時下載)
  Qwen3-ASR-1.7B      ● 已下載

推理核心
  ● Qwen (5 種模型可選)
  ○ Whisper/Breeze (3 種模型可選)

模型: [Qwen3-ASR-0.6B ▼]  GPU: [Auto ▼]
```

**States**:
- 每個模型有狀態：已下載 / 未下載 / 下載中 / 失敗
- 下載中顯示進度條

**API calls**:
- `GET /models/status` (查詢所有模型狀態)
- `POST /models/download/:name` (下載模型)
- `POST /models/recheck` (重新檢查)

---

### P6: 設定 (Settings.tsx)

應用程式偏好設定，類似參考工具的設定頁：

```
設定

介面縮放        [══════●══════]  100%

輸出格式        [SRT 字幕 ●] [純文字]

語音偵測靈敏度  [════●══════]  0.35

每段最長秒數    [════●══════]  30s

簡繁詞彙轉換    [關閉] [台灣用語 ●] [標準]

HuggingFace 鏡像  [hf-mirror.com]

FFmpeg 路徑       [(留空=自動偵測)]

外觀主題        [淺色 ●] [深色] [跟隨系統]

介面語言        [繁體中文 ▼]
```

**States**: 所有設定即時存檔（onChange → POST /settings）

**API calls**:
- `GET /settings` (讀取)
- `POST /settings` (寫入)

---

## API Contract (補充)

除了現有 endpoint，需新增：

| Method | Route | 用途 |
|--------|-------|------|
| POST | `/endpoint/start` | 啟動本機 server |
| POST | `/endpoint/stop` | 停止 server |
| GET | `/endpoint/status` | 目前 URL + QR code data |
| GET | `/models/status` | 所有模型狀態 |
| POST | `/models/download/:name` | 下載特定模型 |
| POST | `/models/recheck` | 重新掃描已下載模型 |
| GET | `/settings` | 讀取 settings.yaml |
| POST | `/settings` | 寫入 settings.yaml |

## Theme

暗色主題（直接沿用 spec.md 的配色方案）：
- Background: `#0f172a`
- Card: `#1e293b`
- Text: `#e2e8f0`
- Accent: `#3b82f6`
- Success: `#22c55e`

## AI Studio Prompt 範例

```prompt
Generate a React TypeScript page component called AudioFile that:
1. Has an upload area showing file name or "選擇檔案" button
2. A button row: Start Conversion, Open Output Folder, Save Subtitles
3. Simple inline settings: language dropdown, speaker diarization toggle, timeline alignment toggle
4. An optional recognition prompt textarea
5. A progress bar
6. Recognition results area with waveform placeholder, word blocks, and subtitle list
7. All API calls go through api.ts (import { api } from '../api')
Use the dark theme colors from the spec. Single page, no routing needed.
```

就是 6 個清晰明確的頁面，每個對應一個 API 互動模式，沒有多餘的抽象層。
