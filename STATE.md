# State — Subtitle Forge

## Project Status
```
Status: In Progress
Branch: feature/local-asr-qwen3
Current Phase: M5 (Backend Enhancement) + M6 (Desktop UX-2) complete
Last Update: 2026-07-17
```

## Done

- [x] **Milestone 1: Codebase Health** (2026-06-26)
- [x] **Milestone 2: UX-1 User Experience** (2026-07-17)
- [x] **Milestone 3: ASR Engine A+B+C** (2026-07-17)
- [x] **Milestone 4: Dual Backend** (2026-07-17)

- [x] **Milestone 5: Backend Enhancement — Mini Tool Parity** (2026-07-17)
  - [x] P1: New API endpoints (audio, waveform, timestamps, QR, pipeline)
  - [x] P2: Pipeline refactor (toggle, VAD, OpenCC, prompt→hot words)
  - [x] P3: Model management (status + download API)
  - [x] P4: Endpoint service (start/stop, auth, port 11435)
  - [x] Code review fixes (shared upload helper, endpoint handler, deprecated cgi)
  - [x] 76 Python tests

- [x] **Milestone 6: Desktop App UX-2** (2026-07-17)
  - [x] Part A: Tauri shell + sidecar + system tray + CORS
  - [x] Part B: React frontend — 6 pages (AudioFile, Batch, Record, Endpoint, ModelManage, Settings)
  - [x] TypeScript zero errors
  - [x] Vite build (266KB, 370ms)

## Pending (BACKLOG)

- G3: Frontend tests (Vitest + MSW) — low priority
- G4: Onboarding UX (welcome screen + model download guide) — low
- G5: Error/Loading/Empty state polish — low
- G6: Version update (Tauri auto-updater) — deferred
- G8: Windows ASR Backend (faster-whisper/OpenVINO) — deferred
- Subtitle Editor (edit timestamps, preview playback)
- Audio/Video Player (polished waveform, word-level seek, speed control)
- UX-3 Polish: notifications, settings panel, output preview — deferred
- recover.py refactoring (396-line recovery engine) — deferred
- Testing expansion (remaining modules) — deferred
- Feature branch → main merge — on hold
