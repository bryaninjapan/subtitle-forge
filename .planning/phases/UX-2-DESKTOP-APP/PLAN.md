# Plan: UX-2 — Desktop App (Tauri + React)

## Goal

Build a professional Desktop GUI for Subtitle Forge. Split into two independent parts:

- **Part A: Tauri Shell + Backend Integration** (由我/Hermes 在 repo 內執行)
- **Part B: React Frontend** (由 Google AI Studio 或外部生成後 merge)

兩部分透過 **API contract**（server.py 的 HTTP endpoints）溝通，可獨立開發。

---

## Part A: Tauri Shell + Backend Integration

### Done Criteria

- [ ] Rust toolchain 安裝 (`rustc`, `cargo`)
- [ ] `desktop/src-tauri/` 專案 scaffolding + 可編譯
- [ ] Tauri sidecar: 啟動時自動 spawn `python3 server.py`
- [ ] Tauri sidecar: 關閉時自動 kill Python process
- [ ] System tray: 圖示、顯示/隱藏視窗、離開
- [ ] 視窗管理: 初始大小、位置、標題、Dock icon
- [ ] 新增 API endpoints: `GET /settings`, `POST /settings`, `POST /cancel/<task_id>`, `GET /outputs/<path>`
- [ ] `GET /progress` 回傳格式加入 `stage`（for 前端 progress bar）
- [ ] CORS 設定（Tauri 前端 call localhost:5000）
- [ ] `.app` 打包 + install script

### Tasks (Part A)

| # | Task | Est. | Description |
|---|------|------|-------------|
| A1 | Install Rust toolchain | 15m | `curl ... https://sh.rustup.rs` |
| A2 | `npm create tauri-app` scaffolding | 30m | 生成 `desktop/` 目錄 |
| A3 | Sidecar config: auto-spawn server.py on launch | 2h | Tauri Rust sidecar + lifecycle |
| A4 | System tray + window management | 2h | tray icon, show/hide, quit |
| A5 | New Python API endpoints | 1h | /settings, /cancel, /outputs/<path> |
| A6 | CORS + API contract verification | 1h | Flask-CORS, test all routes |
| A7 | `.app` packaging + install script | 2h | `cargo tauri build` + `brew`/curl script |

### 架構 (Part A)

```
Tauri .app 啟動時:
  1. Tauri Rust sidecar spawn → python3 server.py (背景)
  2. Sidecar 等待 server.py ready (poll GET /)
  3. 開啟 Tauri webview 視窗 (載入 React 前端)
  4. React 前端 call localhost:5000/api/...

Tauri .app 關閉時:
  1. Rust sidecar send SIGTERM → python3 server.py
  2. 等 5 秒，如果沒關就 SIGKILL
  3. 關閉 webview 視窗
```

---

## Part B: React Frontend (可交由 AI Studio 生成)

### Done Criteria

- [ ] `api.ts` — server.py API 封裝層 (所有 endpoint)
- [ ] `DropZone.tsx` — drag-and-drop 上傳區域
- [ ] `SettingsPanel.tsx` — Simple/Advanced 設定表單
- [ ] `ProgressDisplay.tsx` — 即時進度條 + 階段標籤
- [ ] `TaskHistory.tsx` — 任務歷史表格 + 輸出預覽
- [ ] `BatchManager.tsx` — 多檔佇列、排序、批次執行
- [ ] `VideoPlayer.tsx` — 內建播放器 + 字幕同步
- [ ] `SubtitleEditor.tsx` — 時間軸、文字編輯、speaker 標記
- [ ] `Dashboard.tsx` — 用量統計 + 費用圖表
- [ ] `TerminalEmbed.tsx` — pipeline log 即時顯示
- [ ] `App.tsx` — 路由 + 佈局
- [ ] 所有 component 可獨立運作（透過 mock API data）

### 與 server.py 的 API Contract

所有 UI component 只透過 HTTP 跟 server.py 溝通：

```typescript
// api.ts — 前端唯一的 API 層
const API = {
  // 上傳
  upload: (file: File) => POST  "/upload"          → {task_id, file, status}

  // 進度
  getProgress: () =>           GET   "/progress"    → {[task_id]: {file, pct, stage, message}}

  // 歷史
  getHistory: () =>            GET   "/history"     → [{timestamp, category, detail, cost}]

  // 輸出
  getOutputs: () =>            GET   "/outputs"     → [{name, files: string[]}]
  getOutputFile: (path) =>     GET   "/outputs/:path"

  // 設定 (新增)
  getSettings: () =>           GET   "/settings"    → settings.yaml 內容
  updateSettings: (data) =>    POST  "/settings"    → {status: "ok"}

  // 取消 (新增)
  cancelTask: (taskId) =>      POST  "/cancel/:id"  → {status: "cancelled"}
}
```

### 專案結構 (Part B)

```
desktop/src/
├── api.ts                    # API 封裝層
├── App.tsx                   # 主元件 + 路由
├── main.tsx                  # React 入口
│
├── components/
│   ├── DropZone.tsx           # 拖曳上傳
│   ├── SettingsPanel.tsx      # 設定面板 (Simple/Advanced)
│   ├── ProgressDisplay.tsx    # 進度條
│   ├── TaskHistory.tsx        # 任務歷史
│   ├── BatchManager.tsx       # 批次管理
│   ├── VideoPlayer.tsx        # 播放器
│   ├── SubtitleEditor.tsx     # 字幕編輯器
│   ├── Dashboard.tsx          # 儀表板
│   └── TerminalEmbed.tsx      # Log 顯示
│
├── hooks/
│   ├── useProgress.ts         # 輪詢進度的 hook
│   └── useSettings.ts         # 讀寫設定的 hook
│
└── types.ts                   # TypeScript 型別定義
```

### 開發流程建議 (AI Studio)

1. 先把 `types.ts` 和 `api.ts` 餵給 AI Studio → 它會理解 API contract
2. 每個 component 獨立 prompt：`"create a DropZone component that POST /upload with drag-and-drop"`
3. 用 mock data 開發，最後再接真實 API
4. 完成後 `git checkout desktop/src/` 或手動 merge

---

## 相依圖

```
Part A (Tauri 殼)              Part B (React 前端)
────────────────────           ────────────────────
A1: Install Rust               
A2: Tauri scaffolding          
A3: Sidecar spawn server.py    (可與 Part A 並行開發)
A4: System tray                
A5: New API endpoints          
A6: CORS + integration         
A7: .app packaging              

API Contract (server.py endpoints)
        ↑                            ↓
        └────────── 整合 ───────────┘
          兩部分透過 HTTP 溝通，各自獨立
```

Part A 和 Part B 可**完全平行開發**，最後用 `cargo tauri dev` 整合測試。

---

## Files Changed / Created

### Part A (Hermes 執行)
| File | Change |
|------|--------|
| `desktop/src-tauri/` | **New** — Tauri Rust shell |
| `desktop/src-tauri/src/main.rs` | Sidecar + tray + window |
| `desktop/src-tauri/tauri.conf.json` | Sidecar config |
| `server.py` | New endpoints /settings, /cancel |
| `requirements.txt` | Add flask-cors |

### Part B (AI Studio 或外部)
| File | Change |
|------|--------|
| `desktop/src/` | **New** — React 前端 |
| `desktop/package.json` | **New** |
| `desktop/vite.config.ts` | **New** |
| `desktop/tsconfig.json` | **New** |

## Rollback

```bash
git checkout -- server.py requirements.txt
rm -rf desktop/
```

## Commit Message

```
feat(ux-2): desktop app — Tauri shell + React frontend

Part A: Tauri Shell + Backend Integration
- Rust toolchain + Tauri scaffolding
- Sidecar: auto-spawn server.py on launch
- System tray + window management
- New API: /settings, /cancel, /outputs/<path>
- CORS + integration test
- .app packaging + install script

Part B: React Frontend
- DropZone, SettingsPanel, ProgressDisplay
- TaskHistory, BatchManager
- VideoPlayer, SubtitleEditor
- Dashboard, TerminalEmbed
- api.ts + TypeScript types
```
