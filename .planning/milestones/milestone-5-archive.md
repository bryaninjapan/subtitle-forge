# Milestone 5: Backend Enhancement — Mini Tool Parity — Archive

**Date:** 2026-07-17
**Status:** ✅ Complete

## Goal

Add all missing backend endpoints & pipeline features before building React frontend.

## Phases

| Phase | Status | Deliverables |
|-------|--------|-------------|
| P1: New API endpoints | ✅ | `/audio`, `/waveform`, `/timestamps`, `/pipeline`, `/endpoint/qrcode` |
| P2: Pipeline refactor | ✅ | Toggle (translate/notes/chapters), VAD threshold, OpenCC, prompt→hot words |
| P3: Model management | ✅ | `GET /models/status`, `POST /models/download/:name` |
| P4: Endpoint service | ✅ | Start/stop background server, access key auth, port 11435 |

## Key Decisions

- Waveform peaks computed server-side via ffmpeg (adaptive resolution)
- OpenCC for simplified/traditional conversion (s2t + s2tw)
- Clean up deprecated `cgi.FieldStorage` → manual multipart parser
- Extract `_save_uploaded_file()` helper to eliminate route duplication

## Metrics

| Metric | Value |
|--------|-------|
| New Python tests | +16 |
| Total Python tests | 76 |
