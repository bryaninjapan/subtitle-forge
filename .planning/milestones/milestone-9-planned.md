# Milestone 9: Platform & Infrastructure

**Goal:** 跨平台支援 + 技術債清理 + 版本更新機制。
**Est.:** ~2 週
**Status:** 🔜 Planned

## Phases

| # | Phase | Est. | Description |
|---|-------|------|-------------|
| 1 | Windows ASR Backend (G8) | 1 週 | faster-whisper (CUDA/CPU) or OpenVINO INT8 backend for Windows |
| 2 | recover.py refactoring | 2 天 | Split 396-line recovery engine into focused modules |
| 3 | Onboarding UX (G4) | 2 天 | Welcome screen + model download guide for first-time users |
| 4 | Version update (G6) | 2 天 | Tauri auto-updater based on GitHub Releases |

## Scope Guardrails

- **In scope:** Windows ASR, recover.py cleanup, onboarding, version updates
- **Out of scope:** Subtitle editor improvements (M8 done), Player fixes (M8 done), new UI features
- **Must keep:** 97 Python tests, TypeScript zero errors, Vite build green
