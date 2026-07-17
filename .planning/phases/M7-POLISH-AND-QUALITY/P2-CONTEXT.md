# Phase 2: Frontend Tests (Vitest + MSW) — Decisions

**Date:** 2026-07-17

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Framework | Vitest (Vite-native, zero config) |
| API Mocking | MSW (Mock Service Worker) |
| Scope | Component + Integration tests |
| Priority | AudioFile.tsx first (largest, most APIs) |
| Target | Each page gets 1-2 integration tests min |
| Coverage | Not measured (no coverage target) |

## Plan

1. Install Vitest + MSW + jsdom + testing-library
2. Create test setup (`src/test/setup.ts`)
3. Write MSW handlers for all API endpoints
4. Test AudioFile.tsx (upload → progress → waveform → timestamps)
5. Test Batch.tsx (multiple files → start all → progress)
6. Test Settings.tsx (load → change → save)
7. Add `npm run test` script
