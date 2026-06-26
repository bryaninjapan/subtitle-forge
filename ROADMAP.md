# Subtitle Forge — ROADMAP

## ✓ Milestone 1: Codebase Health + Module Refactoring (Complete 2026-06-26)

**Goal:** Clean up technical debt and refactor monolithic modules.

| Phase | Status | 
|-------|--------|
| 3.1 — Split director.py into director/ package | ✅ `b84bb92` |
| 4 — Split srt_utils + media_utils into focused modules | ✅ `a4be9f6` |
| Cleanup (bare except, imports, config, .env, git hygiene) | ✅ Done |

**Archive:** `.planning/milestones/milestone-1-archive.md`

## Upcoming (No plan yet)

| Phase | Description | Priority |
|-------|-------------|----------|
| 5 — recover.py refactoring | Split 396-line recovery engine | Low |
| Testing expansion | Add tests for remaining modules | Low |
| Feature branch → main merge | Merge feature/local-asr-qwen3 into main | ⏸️ On hold |
