# Phase 2: recover.py Refactoring — Decisions

**Date:** 2026-07-17

## Decisions

| Area | Decision |
|------|----------|
| Structure | Package (`recover/__init__.py` + `__main__.py`) — single file with all functions |
| CLI | `python -m recover scan` / `fix` / `summary` |
| Goal | No functional changes, just clean organization |
