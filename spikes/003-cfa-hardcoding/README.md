# Spike: Survey CFA-Specific Hardcoding

## Question
What parts of the codebase are CFA-specific and would need to be made configurable/generic to support any subtitle domain?

## Findings

### Category 1: Hardcoded Prompt Text (7 files)

LLM prompts baked into source code with CFA-specific instructions.

| File | Content | Severity |
|------|---------|----------|
| `config.py:59` | `"You are a professional CFA subtitle translator..."` | HIGH |
| `config.py:69` | `"Preserve technical acronyms like NPV, IRR, LOS, CFA..."` | HIGH |
| `notes_generator.py:54` | `"You are an expert CFA tutor."` | HIGH |
| `notes_generator.py:63` | `"Exam Focus: ...likely to appear on the CFA exam."` | HIGH |
| `chapter_generator.py:17` | `"You are a CFA academic editor... focusing on CFA LOS..."` | HIGH |
| `translator.py:107` | `"You are a CFA quality editor..."` | HIGH |
| `qa_agent.py:19-23` | `"Financial English translation"`, `"financial/academic tone"` | MEDIUM |

### Category 2: Anki Deck Hardcoded as CFA (2 files)

| File | Content |
|------|---------|
| `anki_exporter.py:12,27` | Deck name: `Subtitle Forge CFA Vocabulary`, `CFA Exam :: Subtitle Forge Terms` |
| `main.py:129` | Output path: `BASE_DIR / "cfa_glossary.apkg"` |

### Category 3: Glossary Extraction Prompt (1 file)

| File | Content |
|------|---------|
| `glossary_manager.py:59` | `"Identify 5-10 technical CFA terms..."` |

### Already Generic (no change needed)

Glossary system (`glossary_manager.py`, `config.py:load_glossary`, translator glossary injection) is domain-agnostic — reads JSON, injects via `{glossary_text}`.

## Verdict: VALIDATED

~15 lines across 4 core files are the main blocker. Fix is mechanical: move prompts to `settings.yaml` with `{domain}` template variable.

## Recommendation

### Minimal path
Add to `settings.yaml`:
- `prompts.translation`, `prompts.study_notes`, `prompts.chapter`, `prompts.qa`, `prompts.glossary_extraction`
- `anki.deck_name`, `anki.output_path`
- All use `{domain}` placeholder (default `"CFA"`)
