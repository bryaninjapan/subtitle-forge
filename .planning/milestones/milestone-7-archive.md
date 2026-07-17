# Milestone 7: Polish & Quality — Archive

**Date:** 2026-07-17
**Status:** ✅ Complete

## Goal

打磨前端品質 — 統一的載入/錯誤/空白狀態、前端測試基礎、UI 細節優化。

## Phases

| Phase | Status | Deliverables |
|-------|--------|-------------|
| P1: Error/Loading/Empty states | ✅ | `SharedStates.tsx` (LoadingSpinner, ErrorBanner, EmptyState) |
| P2: Frontend tests | ✅ | Vitest + MSW + 4 component tests |
| P3: Backend testing expansion | ✅ | 16 new asr_engine pure function tests, 4 new server endpoint tests |
| P4: UX-3 Polish | ✅ | Toast notifications, SRT output preview, settings save feedback |

## Key Decisions

- Shared state components over per-page duplication (Settings.tsx uses shared; others keep inline patterns)
- MSW for API mocking in frontend tests (15 handlers covering all endpoints)
- Toast pattern: global container in App.tsx + `toast()` function (no state management library)
- Backend tests: mock MLX + ffmpeg; test pure functions directly

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Python tests | 75 | **97** (+22) |
| Vitest tests | 0 | **4** |
| TypeScript errors | 0 | **0** |
| asr_engine coverage | 9% | 29% |
| server.py coverage | 59% | 62% |
| Total coverage | 39% | 46% |

## Learnings

- Early return pattern (`if (loading) return <Spinner />`) is cleaner than ternary wrapping for state handling
- Emoji in JSX button text breaks `getByText('exact')` in tests — use regex instead
- AI Studio regenerations reintroduce previously-fixed type errors; `npx tsc --noEmit` needed after every prompt
