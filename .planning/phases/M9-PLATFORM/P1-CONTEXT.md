# Phase 1: Windows ASR Backend (OpenVINO) — Decisions

**Date:** 2026-07-17
**Milestone:** M9 — Platform & Infrastructure

## 🔒 Locked Decisions

| Area | Decision |
|------|----------|
| Backend | OpenVINO WhisperPipeline (openvino-genai) |
| Model | `openvino/whisper-base` (pre-converted) from HuggingFace |
| Architecture | if/else in `_transcribe_with_qwen3_asr()` |
| Model download | Automatic via HuggingFace cache |
| Config | `asr_backend: "openvino"` in settings.yaml |

## Plan

1. Add `asr_backend: openvino` to settings.yaml + config.py
2. Create `transcribe_via_openvino()` in asr_engine.py
3. Wire if/else branch in `_transcribe_with_qwen3_asr()`
4. Add test
5. Add openvino to requirements.txt
