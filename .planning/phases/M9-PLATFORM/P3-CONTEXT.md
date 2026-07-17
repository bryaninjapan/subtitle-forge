# Phase 3: Onboarding UX — Decisions

**Date:** 2026-07-17

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Location | Overlay in App.tsx, shown on first launch |
| Content | 3-step wizard + model download check |
| First-run detection | localStorage `onboardingComplete: true` |

## Plan

1. Create `OnboardingWizard.tsx` component
2. Add first-run check in App.tsx
3. Step 1: Welcome + overview
4. Step 2: Upload file / configure settings
5. Step 3: Model download check (skip if api backend)
6. localStorage flag on completion
