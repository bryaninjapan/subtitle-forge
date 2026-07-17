# Plan: ASR Engine Enhancement — Phase A + B + C

## Goal

Upgrade subtitle-forge's local ASR engine with:
1. **ForcedAligner + Hot Words** (方案3) — word-level timestamps + glossary correction
2. **VAD + Diarization** — better silence detection + speaker separation
3. **Accuracy boost** — script matching + smart line splitting
4. **Performance** — speculative decoding, async batch, long audio chunking

## Done Criteria

- [ ] ASR model / aligner model 路徑在 `settings.yaml`（不再硬編碼）
- [ ] ASR 產出 word-level timestamps（ForcedAligner）
- [ ] Glossary 術語自動校正 ASR 辨識錯誤（熱詞）
- [ ] Silero VAD 取代 ffmpeg silence check
- [ ] Speaker diarization（說話者分離）
- [ ] `--script` 旗標載入參考文稿 → ASR 校準
- [ ] 智能拆行：語義邊界（句號）優先於 max_chars
- [ ] Speculative decoding 加速長音頻
- [ ] Async/batch 平行轉錄
- [ ] 長音頻自動 chunking + 合併
- [ ] `pytest tests/ -x` 通過

---

## Tasks

| # | Task | Est. | Deps | Wave |
|---|------|------|------|------|
| A4 | Model path → settings.yaml | 45m | — | 1 |
| A1 | ForcedAligner word-level timestamps | 2h | A4 | 2 |
| B1 | Hot words: glossary correction | 2h | A1 | 3 |
| A2 | Silero VAD | 2h | — | 1 |
| A3 | Speaker Diarization | 1h | — | 1 |
| B2 | Script matching (--script) | 3h | A1 | 3 |
| B3 | Smart line splitting | 2h | A1 | 3 |
| C1 | Speculative decoding | 1h | A4 | 2 |
| C2 | Async/batch parallelism | 2h | — | 1 |
| C3 | Long audio chunking | 2h | — | 2 |

---

## Dependency Graph

```
Wave 1 (parallel, 3 max)
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│  A4  │ │  A2  │ │  A3  │ │  C2  │
│model │ │ VAD  │ │Diari-│ │Async │
│→yaml │ │      │ │zation│ │batch │
└──┬───┘ └──────┘ └──────┘ └──────┘
   │
   ▼
Wave 2 (parallel)
┌──────┐ ┌──────┐ ┌──────┐
│  A1  │ │  C1  │ │  C3  │
│Force-│ │Spec. │ │Chunk │
│Align │ │Decode│ │      │
└──┬───┘ └──────┘ └──────┘
   │
   ▼
Wave 3 (parallel)
┌──────┐ ┌──────┐ ┌──────┐
│  B1  │ │  B2  │ │  B3  │
│Hot   │ │Script│ │Smart │
│Words │ │Match │ │Split │
└──────┘ └──────┘ └──────┘

Critical Path: A4 → A1 → B1 (~3 days)
```

---

## Task Details

### A4: Model path → settings.yaml (45min)
- Add to `settings.yaml`:
  ```yaml
  asr:
    model: "Qwen/Qwen3-ASR-0.6B"
    aligner_model: "Qwen/Qwen3-ForcedAligner-0.6B"
  ```
- `config.py`: read `asr.model` and `asr.aligner_model`
- `asr_engine.py`: replace `QWEN3_ASR_MODEL` constant with config lookup
- Fallback to current hardcoded value if key missing (backward compat)

### A1: ForcedAligner word-level timestamps (2h)
- `from mlx_qwen3_asr import ForcedAligner`
- After ASR produces text, run ForcedAligner to get word-level timestamps
- Replace current segment-level `_group_words_into_subtitles()` with word-level SRT
- Each word gets its own SRT entry (or group by phrase)
- Log number of words aligned

### B1: Hot words via glossary correction (2h)
- Load glossary from `glossary.json` for current `domain`
- After ASR + ForcedAligner, scan transcript for glossary terms
- Case-insensitive matching (e.g. "npv" → "NPV", "irr" → "IRR")
- Replace misrecognized terms with correct glossary form
- Log: "Hot words corrected: NPV (3 times), IRR (2 times)"
- Flag `--no-hotwords` to disable

### A2: Silero VAD (2h)
- `pip install silero-vad`
- Replace `check_silence()` ffmpeg silencedetect with `silero_vad`
- Load VAD model once, cache it
- Benefits: more accurate, detects speech vs silence at word level
- Returns speech timestamps → can be used for smarter chunking

### A3: Speaker Diarization (1h)
- Add `diarize=True` to `transcribe()` call
- Configurable `diarization_num_speakers` via settings.yaml
- Output: "Speaker 1: ..." / "Speaker 2: ..." in SRT
- Default: auto-detect (2-4 speakers)

### B2: Script matching (3h)
- New `--script path/to/reference.txt` flag
- Load reference text (plain text or SRT)
- Use ForcedAligner to align ASR output with reference
- Where confidence is high, replace ASR text with reference text
- Useful for CFA videos with known slides content

### B3: Smart line splitting (2h)
- Replace `_group_words_into_subtitles()` with semantic-aware algorithm:
  - Prefer sentence boundaries (。！？.!?\n)
  - Within max_chars (80) but break at punctuation first
  - Keep short phrases together (don't split 2-word sentences)
  - Consider speaking rate (fast speech = shorter lines)

### C1: Speculative decoding (1h)
- Add `draft_model=QWEN3_ASR_MODEL` to `transcribe()` call
- Same model as draft (or smaller) — benchmark speedup
- Only for long audio (>10 min), skip for short files

### C2: Async/batch parallelism (2h)
- Replace sequential `for f in files: transcribe(f)` with `transcribe_batch(files)`
- Or: use threading with `transcribe_async()` for concurrent files
- Update `director.py` to dispatch ASR jobs in parallel
- Respect `asr_concurrent` config

### C3: Long audio chunking (2h)
- Split audio >30min into 10-min chunks (with overlap)
- Transcribe each chunk separately
- Merge results with timestamp offset correction
- Handle chunk boundaries gracefully (no cut-off words)

---

## Files Changed

| File | Change |
|------|--------|
| `asr_engine.py` | ForcedAligner, hot words, VAD, diarization, speculative decoding, chunking |
| `config.py` | Read ASR model/aligner from settings.yaml |
| `settings.yaml` | Add `asr.model`, `asr.aligner_model`, `vad.enabled`, `diarization` |
| `srt_utils.py` | Smart line splitting algorithm |
| `director/engine.py` | Async batch ASR dispatch |
| `requirements.txt` | Add `silero-vad` |

## Rollback

```bash
git checkout -- asr_engine.py config.py settings.yaml srt_utils.py director/engine.py requirements.txt
```

## Commit Message

```
feat(asr): Phase A+B+C — ForcedAligner, hot words, VAD, diarization, performance

Phase A-1: ForcedAligner + Hot Words
- Move ASR/aligner model paths to settings.yaml
- Integrate ForcedAligner for word-level timestamps
- Glossary-based hot words correction

Phase A-2: VAD + Diarization
- Replace ffmpeg silencedetect with Silero VAD
- Enable speaker diarization (diarize=True)

Phase B: Accuracy
- Script matching via --script flag
- Semantic-aware smart line splitting

Phase C: Performance
- Speculative decoding for long audio
- Async/batch parallel transcription
- Long audio chunking + merge
```
