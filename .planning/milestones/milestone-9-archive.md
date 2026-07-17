# Milestone 9: Platform & Infrastructure — Archive

**Date:** 2026-07-17
**Status:** ✅ Complete

## Goal

跨平台支援 + 技術債清理 + 版本更新機制。

## Phases

| Phase | Status | Deliverables |
|-------|--------|-------------|
| P1: OpenVINO ASR | ✅ | `transcribe_via_openvino()`, `asr_backend: openvino` config |
| P2: recover.py refactor | ✅ | 397-line file → `recover/` package with `python -m recover` CLI |
| P3: Onboarding UX | ✅ | 3-step wizard overlay, localStorage detection |
| P4: Version update | ✅ | `tauri-plugin-updater`, GitHub Releases endpoint, Settings button |

## Key Decisions

- OpenVINO WhisperPipeline over faster-whisper (matches reference tool approach)
- recover.py → single-file package with sub-functions organized by concern
- Onboarding: overlay not sidebar — first-impression UX
- Version update: manual check, not auto-check — less intrusive
- Dynamic `import()` for updater to work in both Tauri and browser dev mode

## Metrics

| Metric | Value |
|--------|-------|
| Python tests | 97 |
| TypeScript errors | 0 |
| Vite build | 275KB |
| New packages | openvino, openvino-genai, @tauri-apps/plugin-updater |
