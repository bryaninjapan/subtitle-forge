# Subtitle Forge — ROADMAP

## ✓ Milestone 1: Codebase Health + Module Refactoring (Complete 2026-06-26)

**Goal:** Clean up technical debt and refactor monolithic modules.

| Phase | Status | 
|-------|--------|
| 3.1 — Split director.py into director/ package | ✅ `b84bb92` |
| 4 — Split srt_utils + media_utils into focused modules | ✅ `a4be9f6` |
| Cleanup (bare except, imports, config, .env, git hygiene) | ✅ Done |

**Archive:** `.planning/milestones/milestone-1-archive.md`

## ✓ Milestone 2: User Experience Enhancement UX-1 (Complete 2026-07-17)

**Goal:** Make subtitle-forge more user-friendly (CLI + Web Dashboard + Notifications).

| Phase | Status |
|-------|--------|
| ASR model 1.7B → 0.6B | ✅ Done |
| UX-1 — CLI interactive + completion + notification + web dashboard | ✅ Done |

**Archive:** `.planning/milestones/milestone-2-ux1.md`

## ✓ Milestone 3: ASR Engine Phase A+B+C (Complete 2026-07-17)

**Goal:** Upgrade local ASR with ForcedAligner, VAD, diarization, hot words, script matching, smart splitting, and performance optimizations.

| Phase | Status |
|-------|--------|
| A-1: ForcedAligner + Hot Words | ✅ Done |
| A-2: VAD + Diarization | ✅ Done |
| B: Script Matching + Smart Splitting | ✅ Done |
| C: Speculative Decoding + Async Batch + Chunking | ✅ Done |

**Archive:** `.planning/milestones/milestone-3-asr-abc.md`

## ✓ Milestone 4: Dual Backend + UX Enhancements (Complete 2026-07-17)

**Goal:** Add OpenRouter API ASR backend, on_progress callback, batch burn-in.

| Phase | Status |
|-------|--------|
| on_progress callback | ✅ Done |
| Batch burn-in (--burn) | ✅ Done |
| OpenRouter Whisper API backend | ✅ Done |
| Dual backend switch (local/api) | ✅ Done |

**Planning:** `.planning/phases/ASR-DUAL-BACKEND/`

## ✓ Milestone 5: Backend Enhancement — Mini Tool Parity (Complete 2026-07-17)

**Goal:** Add all missing backend endpoints & pipeline features before building React frontend.

| Phase | Status |
|-------|--------|
| P1 — New API endpoints (audio, waveform, timestamps, QR, pipeline) | ✅ Done |
| P2 — Pipeline refactor (toggle, VAD, OpenCC, prompt→hot words) | ✅ Done |
| P3 — Model management (status + download API) | ✅ Done |
| P4 — Endpoint service (start/stop, auth, port 11435) | ✅ Done |
| Code review fixes | ✅ Done |
| 76 Python tests | ✅ Pass |

**Planning:** `.planning/phases/BACKEND-MISSING/`

## ✅ Milestone 6: Desktop App UX-2 (Complete 2026-07-17)

**Goal:** Professional Desktop GUI via Tauri + React.

| Phase | Status |
|-------|--------|
| Part A — Tauri shell, sidecar, system tray, CORS | ✅ Done |
| Part B — React frontend via AI Studio (8 prompts) | ✅ Done |
| - AudioFile.tsx (upload, playback, waveform, subtitles) | ✅ |
| - Batch.tsx (multi-file queue, progress, status) | ✅ |
| - Record.tsx (recording UI with simulated speech) | ✅ |
| - Endpoint.tsx (service toggle, QR, API key, Cloudflare) | ✅ |
| - ModelManage.tsx (model cards, download, inference switch) | ✅ |
| - Settings.tsx (VAD, CC conversion, format, theme) | ✅ |
| TypeScript zero errors | ✅ |
| Vite build (266KB, 370ms) | ✅ |

**Planning:** `.planning/phases/UX-2-DESKTOP-APP/`

## Backlog (No plan yet)

| Phase | Description | Est. | Priority |
|-------|-------------|------|----------|
| Subtitle Editor | 字幕列表可編輯、校正時間軸、即時預覽播放 | M8 | Low |
| Audio/Video Player | 精美波形播放器、逐字跳播、速度控制、播放進度同步 | M8 | Low |
| UX-3 — Polish | Notifications, settings panel, output preview | M7 | Low |
| Frontend tests (Vitest + MSW) | Component + integration tests | M7 | Low |
| Backend testing expansion | More test coverage | M7 | Low |
| Error/Loading/Empty states | Polish component status states | M7 | Low |
| Onboarding UX (G4) | Welcome screen + model download guide | M9 | Low |
| Windows ASR Backend (G8) | faster-whisper/OpenVINO | M9 | Low |
| recover.py refactoring | Split 396-line recovery engine | M9 | Low |
| Version update (G6) | Tauri auto-updater | M9 | Low |
| Feature branch → main merge | Merge into main | Final | ⏸️ On hold |

## 📅 Planned Milestones

## ✅ M7: Polish & Quality (Complete 2026-07-17)
**Goal:** 打磨前端品質 — 統一的載入/錯誤/空白狀態、前端測試基礎、UI 細節優化。

| Phase | Status |
|-------|--------|
| P1 | Error/Loading/Empty states (G5) | ✅ |
| P2 | Frontend tests (Vitest + MSW) (G3) | ✅ |
| P3 | Backend testing expansion | ✅ |
| P4 | UX-3 Polish (notifications, settings panel, output preview) | ✅ |
| Code review | ✅ Passed |
| Tests | 97 Python + 4 Vitest + 0 TS errors |

## ✅ M8: Feature Completion (Complete 2026-07-17)
**Goal:** 補上參考工具最關鍵的遺漏功能 — 字幕編輯 + 精美播放器。

| Phase | Status |
|-------|--------|
| P1 — Subtitle Editor | ✅ |
| P2 — Audio/Video Player | ✅ |
| Inline editing, speed control, keyboard shortcuts | ✅ |
| TypeScript 0 errors, Python 97 tests | ✅ |

## ✅ M9: Platform & Infrastructure (Complete 2026-07-17)
**Goal:** 跨平台支援 + 技術債清理 + 版本更新機制。

| Phase | Status |
|-------|--------|
| P1 — Windows ASR Backend (OpenVINO) | ✅ |
| P2 — recover.py refactoring | ✅ 397→package |
| P3 — Onboarding UX | ✅ 3-step wizard |
| P4 — Version update (Tauri auto-updater) | ✅ |
| Code review passed | ✅ 0 issues |

### Final: Merge feature → main
**Goal:** 穩定版本合併到主分支。

| Phase | Description |
|-------|-------------|
| P1 | Resolve conflicts, verify build, merge to main |
