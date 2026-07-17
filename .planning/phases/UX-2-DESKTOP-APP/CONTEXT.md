# UX-2 — Desktop GUI (Tauri + React)

**決策鎖定日期:** 2026-07-17

## 🔒 Locked Decisions

### 技術選型
- **Desktop 框架:** Tauri + React
- **後端通訊:** 透過 HTTP call 既有 `server.py` (Flask REST API)
- **Python 後端:** 現有 server.py 不需改動，新增 API endpoint 按需補

### Scope — UX-2 Full

| 功能 | 說明 |
|------|------|
| 📁 Drag-and-drop 上傳 | 桌面原生拖曳，支援單檔/多檔 |
| ⚙️ Simple/Advanced 設定面板 | Simple: 語言 + ASR 來源; Advanced: model, hot words, concurrency, API keys |
| 📊 即時進度 | 比 HTMX polling 更流暢的 UI 更新 |
| 📋 任務歷史 + 輸出預覽 | 從 server.py API 讀取，React 前端渲染 |
| 🖥️ 獨立 .app | Dock icon、選單列、獨立視窗 |
| 🪟 System tray | 背景常駐，點 tray icon 開關視窗 |
| 📂 批次管理 | 多檔排序、隊列管理 |
| 🎬 內建播放器 | 預覽影片 + 字幕同步顯示 |
| ✏️ 字幕編輯器 | 時間軸調整、文字編輯、speaker 標記 |
| 🔄 一鍵切換 Local/API ASR | 設定面板切換，不重啟 |
| 📊 Dashboard | 用量統計、費用圖表 |
| 🐚 Terminal 內嵌 | pipeline log 即時顯示 |

### 設定設計

- **Simple/Advanced 同一表單**，Advanced 預設折疊
- 所有設定存到 `settings.yaml`，跟 CLI 共用
- Simple mode: 語言 + ASR 來源 (Local/API toggle)
- Advanced mode: model 選擇、hot words、concurrency、API keys、style、output format、max cost

### Distribution (TBD)
- **建議先走方案 A**: 使用者先裝 Python + venv，Tauri 負責前端 .app
- 安裝腳本輔助: `curl ... | bash` 自動建 venv + install deps
- UX-2 穩定後再考慮 bundle Python runtime 或 Homebrew

## 📋 API Contract (React → server.py)

React 前端只透過 HTTP 跟 server.py 溝通，現有 endpoint 已夠用：

| Method | Route | React 用途 |
|--------|-------|------------|
| `POST` | `/upload` | 上傳檔案，取得 task_id |
| `GET` | `/progress` | polling 讀取所有 task 進度 |
| `GET` | `/history` | 任務歷史列表 |
| `GET` | `/outputs` | 輸出目錄瀏覽 |
| `GET` | `/outputs/<path>` | (新增) 下載/預覽特定檔案 |

**可能新增的 endpoint:**
- `GET /settings` — 讀取 settings.yaml
- `POST /settings` — 寫入 settings.yaml
- `POST /cancel/<task_id>` — 取消進行中的 task

## 📁 專案結構 (建議)

```
subtitle-forge/
├── server.py              # 不變，Flask API
├── main.py                # 不變，CLI
├── asr_engine.py          # 不變
├── ...                    # 所有現有 Python 不變
│
├── desktop/               # 新增 — Tauri + React 前端
│   ├── src-tauri/         # Tauri Rust 殼
│   │   ├── src/main.rs    # sidebar, tray, window management
│   │   └── tauri.conf.json
│   ├── src/               # React 前端
│   │   ├── App.tsx
│   │   ├── components/    # DropZone, Settings, Progress, History...
│   │   ├── pages/         # 各頁面
│   │   └── api.ts         # server.py API wrapper
│   ├── package.json
│   └── vite.config.ts
│
└── requirements.txt       # 不變
```

## ⏱️ 預估時間

- Tauri + React 環境建置 + 通訊驗證: 2-3 天
- Simple/Advanced 設定面板: 2-3 天
- Drag-drop + 進度 + 歷史: 2-3 天
- 批次管理 + 播放器 + 字幕編輯器: 1 週
- System tray + Dashboard + Terminal: 2-3 天
- 打包 + 安裝腳本: 1-2 天
- **總計: ~3-4 週**
