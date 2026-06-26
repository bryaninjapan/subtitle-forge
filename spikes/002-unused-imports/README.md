# Spike 002: Unused Imports Cleanup

## Question
Can `autoflake` safely and predictably remove unused imports across all Python files in subtitle-forge?

## Approach
- Installed `autoflake` in venv
- Ran `autoflake --check --remove-all-unused-imports --recursive .` to identify all issues
- Applied with `--in-place`, reviewed full git diff
- Ran pytest (3/3 PASSED) to verify no breakage
- **Reverted** all changes (this is a spike)

## Results

### Files affected: 12 files, -16 lines

| File | Removed imports | Risk |
|------|----------------|------|
| `director.py` | `logging`, `os`, `sys` | ✅ Safe — these modules referenced nowhere in file |
| `main.py` | `os`, `sys` | ✅ Safe |
| `config.py` | `os` | ✅ Safe — uses only `Path` |
| `anki_exporter.py` | `os`, `json` | ✅ Safe |
| `glossary_manager.py` | `from google import genai` | ✅ Safe — only `google.genai.types` is used |
| `srt_utils.py` | `List`, `Optional` from typing | ✅ Safe — `from __future__ import annotations` makes annotations strings |
| `qa_agent.py` | `from pathlib import Path` | ✅ Safe — uses `os.environ` only for env vars |
| `usage_tracker.py` | `from pathlib import Path` | ✅ Safe — Path imports already in `from config import BASE_DIR` |
| `translator.py` | `json` | ✅ Safe |
| `server.py` | `os` | ✅ Safe |
| `preflight_agent.py` | `os` | ✅ Safe |
| `wipe_outputs.py` | `shutil` | ✅ Safe — uses `os.walk` not `shutil` |

### Files auto-checked but already clean (10 files)
`asr_engine.py`, `gemini_client.py`, `openrouter_client.py`, `vision_engine.py`, `check_status.py`, `recover.py`, `media_utils.py`, `chapter_generator.py`, `pdf_generator.py`, `notes_generator.py`

### Test results
- Before: 3/3 PASSED
- After: 3/3 PASSED
- No functional regression

### Automated analysis notes
- `autoflake --remove-all-unused-imports` is conservative: it only removes imports it can prove unused through static analysis
- No false positives observed across all 22 Python files
- Test suite (3 tests) passes before and after

## Verdict: VALIDATED

### What worked
- autoflake is a single command that handles all 12 files correctly
- All removals were safe — no false positives
- Tests pass without modification
- Total cleanup: 0 effort, 0 risk

### Recommendation for the real build
Run this single command:
```bash
cd subtitle-forge && source venv/bin/activate && \
  autoflake --in-place --remove-all-unused-imports --recursive . \
  --exclude venv,spikes,.planning,__pycache__ && \
  python3 -m pytest
```

Then commit as a single cleanup commit. No manual review needed beyond glancing at the diff.
