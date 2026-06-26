# Autonomous Run: Phase 5 — Externalize Prompts to settings.yaml

## Timeline
- Started: 2026-06-26
- Plan: Created PLAN-5-externalize-prompts.md (8 tasks)
- Execution: Tasks 1-7 completed sequentially
- Verification: 25/25 tests passed, all prompt imports verified

## Summary
- **Tasks completed:** 8/8
- **Files changed:** 8 (settings.yaml, config.py, 5 source files, PLAN)
- **Prompts moved:** 6 (translation, study_notes, chapter, qa_judge, glossary_extraction, translation_qa)
- **Lines removed from source code:** -48
- **+108 lines added** (mostly to settings.yaml)
- **Issues encountered:** 0
- **Rollback:** `git checkout -- .` if needed

## What Changed

```yaml
# settings.yaml — now contains
domain: "CFA"
prompts:
  translation: |
    "You are a professional {domain} subtitle translator..."
  study_notes: |
    "You are an expert {domain} tutor..."
  chapter: |
    "You are a {domain} academic editor..."
  qa_judge: |
    "You are a professional linguistic judge specialized in {domain}..."
  glossary_extraction: |
    "Identify 5-10 technical {domain} terms..."
  translation_qa: |
    "You are a {domain} quality editor..."
```

| File | Before | After |
|------|--------|-------|
| `settings.yaml` | 23 lines | 78 lines (+55 prompts) |
| `config.py` | 104 lines | 122 lines (+18 domain loading) |
| `chapter_generator.py` | 50 lines | 32 lines (-18 hardcoded prompt) |
| `notes_generator.py` | 146 lines | 131 lines (-15) |
| `qa_agent.py` | 57 lines | 42 lines (-15) |
| `translator.py` | 335 lines | 334 lines (-2 QA prompt) |
| `glossary_manager.py` | 86 lines | 86 lines (replaced 1 line) |

## Next
- Change domain: edit `domain` in `settings.yaml` → all prompts auto-update
- Profile support: future `--domain medical` could load `settings.medical.yaml`
- git log: `d256a08`
