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

| Phase | Description | Priority |
|-------|-------------|----------|
| **Subtitle Editor** | 字幕列表可編輯、校正時間軸、即時預覽播放 | Low |
| **Audio/Video Player** | 精美波形播放器、逐字跳播、速度控制、播放進度同步 | Low |
| UX-3 — Polish | Notifications, settings panel, output preview | Low |
| recover.py refactoring | Split 396-line recovery engine | Low |
| Testing expansion | Add tests for remaining modules | Low |
| Feature branch → main merge | Merge feature/local-asr-qwen3 into main | ⏸️ On hold |
