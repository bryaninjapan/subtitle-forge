# Phase 4: UX-3 Polish — Decisions

**Date:** 2026-07-17

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Toast | Right-top floating toast, auto-dismiss 3s, green/red variants |
| Settings | Add scaling slider, output format toggle, save feedback |
| Output preview | SRT raw text in AudioFile page below subtitle list |

## Plan

1. Create `Toast` component + `useToast` hook
2. Add toast to AudioFile (on completion/error), Settings (on save)
3. Polish Settings page (scaling slider visual, save feedback)
4. Add output preview section to AudioFile
