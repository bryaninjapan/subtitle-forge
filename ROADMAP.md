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

## 🔄 Milestone 5: Desktop App UX-2 (Planned)

**Goal:** Professional Desktop GUI via Tauri + React.

| Phase | Description | Priority | Est. |
|-------|-------------|----------|------|
| UX-2 — Tauri + React Desktop GUI | Full desktop app: upload, settings, progress, batch, player, subtitle editor, tray | High | 3-4 wks |

**Context:** `.planning/phases/UX-2-DESKTOP-APP/CONTEXT.md`

## Backlog (No plan yet)

| Phase | Description | Priority |
|-------|-------------|----------|
| UX-3 — Polish | Notifications, settings panel, output preview | Low |
| recover.py refactoring | Split 396-line recovery engine | Low |
| Testing expansion | Add tests for remaining modules | Low |
| Feature branch → main merge | Merge feature/local-asr-qwen3 into main | ⏸️ On hold |
