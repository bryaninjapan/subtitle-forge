# Plan: UX-2 — Desktop GUI (Tauri + React)

## Goal

Build a professional Desktop GUI for Subtitle Forge using **Tauri + React**, wrapping the existing Flask backend into a standalone `.app` with drag-drop upload, real-time progress, settings panel (Simple/Advanced), batch management, video player, subtitle editor, and system tray.

## Pre-flight Checklist

- [ ] Node.js v22 ✅ (`node --version`)
- [ ] npm 10.9 ✅ (`npm --version`)
- [ ] Rust toolchain ❌ → needs install (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- [ ] Python 3 + venv ✅ (existing)
- [ ] `server.py` Flask API ✅ (existing)
- [ ] 全 48 tests pass ✅

## Done Criteria

- [ ] `.app` 可獨立啟動，自動背景 spawn `python3 server.py`
- [ ] Drag-and-drop 上傳影片 → 觸發完整 pipeline
- [ ] Simple/Advanced 設定面板：Simple (語言 + ASR 來源), Advanced (model, hot words, concurrency, API key)
- [ ] 即時進度條 + 任務歷史 + 輸出預覽
- [ ] 批次管理（多檔排序、佇列、一鍵執行）
- [ ] 內建播放器 + 字幕同步顯示
- [ ] 字幕編輯器（時間軸、文字編輯、speaker 標記）
- [ ] System tray（背景常駐、點開即用）+ Dashboard（用量統計）
- [ ] Terminal 內嵌（即時 pipeline log）
- [ ] Model 下載 UX（首次使用 ASR model 時顯示進度）
- [ ] 首次執行引導（onboarding：側邊欄提示 + server 狀態檢查）
- [ ] Error / Loading / Empty state 覆蓋（斷線、失敗、無任務）
- [ ] ASR model / aligner model 路徑移至 `settings.yaml`（Gap 1）
- [ ] 前端 Component + Integration 測試
- [ ] 所有現有 CLI + Web Dashboard 不受影響
- [ ] Tests: `pytest tests/ -x` + `cd desktop && npm test`

---

## Sub-phase A: Foundation (Week 1)

| # | Task | Est. | Deps |
|---|------|------|------|
| A1 | Install Rust + Tauri CLI + `npm create tauri-app` scaffolding | 1h | Pre-flight |
| A2 | **Phase A4**: ASR model / aligner model 路徑移至 `settings.yaml` | 45m | — |
| A3 | New Python API endpoints: `/settings`, `/models/status`, `/models/download`, `/cancel/<task_id>` | 2h | — |
| A4 | Tauri sidecar config: auto-spawn `python3 server.py` on app launch | 2h | A1 |
| A5 | React 專案基礎：Vite + TypeScript + API client module (`api.ts`) + 路由 | 2h | A1 |
| A6 | server.py 前綴 `/api/v1`（或保留現有 routes，React 直接 call） | 30m | — |

**Verification gate (End of Week 1):**
- `cargo tauri dev` 啟動後，React 畫面顯示「Connected to server」
- `GET /settings` 回傳 `settings.yaml` 內容
- `GET /models/status` 回傳 model 下載狀態
- `pytest tests/ -x` 仍全數通過

---

## Sub-phase B: Core Desktop UI (Week 2)

| # | Task | Est. | Deps |
|---|------|------|------|
| B1 | **Settings Panel**: Simple mode (language, ASR source toggle) + Advanced mode (model, hot words, concurrency, API key, style, output format) — collapsible sections | 2d | A3, A5 |
| B2 | **Drag-drop Zone** + file validation + POST `/upload` | 1d | A5 |
| B3 | **Progress Display**: polling `/progress`, animated progress bars, stage labels | 1d | A5, B2 |
| B4 | **Task History + Output Browser**: `/history` + `/outputs` tables, file preview | 1d | A5 |
| B5 | **Error / Loading / Empty States** (G5): server disconnected, pipeline failed, no tasks, upload error | 1d | B2, B3, B4 |
| B6 | **Model Download UX** (G2): download progress UI + integrity check | 1d | A3, A5 |

**Verification gate (End of Week 2):**
- Drag video → select local ASR → settings persist → progress animates → history shows result
- Model download shows progress bar
- Mock server disconnect shows "Connection lost" state
- Empty state shown when no history

---

## Sub-phase C: Advanced Features (Week 3-4)

| # | Task | Est. | Deps |
|---|------|------|------|
| C1 | **Batch Management**: multi-file queue, sort, drag-reorder, batch start | 2d | B2, B3 |
| C2 | **System Tray**: tray icon, show/hide window, quit, status badge | 1d | A4, A5 |
| C3 | **Dashboard**: usage stats, cost chart, task completion rate (from `usage_log.jsonl`) | 1d | B4 |
| C4 | **Video Player + Subtitle Sync**: HTML5 `<video>` + subtitle overlay | 2d | B4 |
| C5 | **Subtitle Editor**: timeline scrub, text edit, speaker labels, add/delete entries, save | 3d | C4 |
| C6 | **Terminal Embed**: pipeline log stream (SSE or polling `/progress`) | 1d | B3 |
| C7 | **Onboarding Flow** (G4): first-launch welcome, server status check, model download guide, tooltips | 1d | A4, B1, B6 |
| C8 | **React Component Tests** (G3): Vitest + Testing Library for key components (Settings, DropZone, Progress) | 2d | B1-B6 |
| C9 | **Packaging**: `cargo tauri build` → `.dmg` / install script | 1d | All |

**Verification gate (End of Week 4):**
- Full desktop app with all features working
- `cd desktop && npm test` passes
- `cargo tauri build` produces .dmg
- Existing CLI + Web Dashboard unaffected

---

## Dependency Graph

```
Week 1                    Week 2                         Week 3-4
┌──────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐
│ A1: Tauri env │    │ B1: Settings Panel   │    │ C1: Batch Management     │
│ A2: settings  │───→│ B2: Drag-drop +Upload│───→│ C2: System Tray          │
│  .yaml (G1)   │    │ B3: Progress Display │    │ C3: Dashboard            │
│ A3: Python API│───→│ B4: History + Outputs│───→│ C4: Video Player         │
│ A4: Sidecar   │    │ B5: Error/Empty State│    │ C5: Subtitle Editor      │
│ A5: React base│───→│ B6: Model Download UX│───→│ C6: Terminal Embed       │
│ A6: API prefix│    │                     │    │ C7: Onboarding Flow      │
└──────────────┘    └──────────────────────┘    │ C8: Frontend Tests       │
                                                 │ C9: Package (.dmg)      │
                                                 └──────────────────────────┘
```

### Critical Path (longest sequential chain)
```
A1 → A5 → B2 → B3 → C1 → C4 → C5 → C9
```
**Estimated: ~17 working days** (~3.5 weeks)

---

## Files Changed / Created

### New files
| File | Purpose |
|------|---------|
| `desktop/src-tauri/` | Tauri Rust shell (sidecar, tray, window) |
| `desktop/src/` | React frontend (components, pages, api.ts) |
| `desktop/package.json` | npm dependencies |
| `desktop/vite.config.ts` | Vite config |
| `desktop/src-tauri/tauri.conf.json` | Tauri config (window, sidecar, bundle) |
| `desktop/src-tauri/icons/` | App icons |

### Modified files
| File | Change |
|------|--------|
| `asr_engine.py` | `QWEN3_ASR_MODEL` → read from `settings.yaml` |
| `server.py` | New endpoints: `/settings`, `/models/*`, `/cancel/<task_id>` |
| `settings.yaml` | Add `asr.model`, `asr.aligner_model` keys |
| `config.py` | Read ASR model from settings.yaml |
| `.gitignore` | Add `desktop/src-tauri/target/` |

---

## Rollback

```bash
# Revert code changes
git checkout -- asr_engine.py server.py config.py settings.yaml

# Remove desktop dir
rm -rf desktop/
```

## Commit Message

```
feat(ux-2): professional Desktop GUI with Tauri + React (Milestone 3)

Sub-phase A — Foundation
- Install Rust + Tauri scaffolding + React/Vite base
- Move ASR model path to settings.yaml (Phase A4)
- New Python API: /settings, /models/*, /cancel/<task_id>
- Tauri sidecar: auto-spawn server.py on launch

Sub-phase B — Core Desktop UI
- Simple/Advanced settings panel (language, ASR source, model, hot words...)
- Drag-drop upload + file validation
- Real-time progress bar with stage labels
- Task history + output browser
- Error / Loading / Empty state coverage
- Model download UX with progress

Sub-phase C — Advanced Features
- Batch queue management (sort, reorder, batch start)
- System tray + Dashboard (usage stats, cost chart)
- Video player + subtitle sync overlay
- Subtitle editor (timeline, text, speaker labels)
- Terminal embed for pipeline logs
- Onboarding flow (first-launch guide)
- Frontend component tests (Vitest + Testing Library)
- .dmg packaging + install script

All existing CLI + Web Dashboard unaffected.
```
