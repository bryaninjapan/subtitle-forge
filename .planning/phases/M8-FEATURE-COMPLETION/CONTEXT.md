# Phase 1-2: Subtitle Editor + Player — Decisions

**Date:** 2026-07-17
**Milestone:** M8 — Feature Completion

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Edit mode | Frontend only (no backend API needed) |
| Edit UI | Inline editing (click subtitle text → editable input) |
| Speed control | 0.5x / 1x / 1.5x / 2x buttons |
| Waveform highlight | Played portion turns accent color |
| Keyboard shortcuts | Space = play/pause |
| Waveform zoom | ❌ Skip (too complex for now) |

## Plan

1. Modify AudioFile.tsx subtitle list → inline editing
   - Double-click subtitle text → becomes editable input
   - Enter or blur → save to local state
   - Tab → move to next subtitle
2. Add playback speed control buttons
3. Add keyboard shortcuts (space key handler)
4. Make waveform show playback position (played portion highlighted)

## Files to modify
- `desktop/src/pages/AudioFile.tsx` (primary — all changes here)
