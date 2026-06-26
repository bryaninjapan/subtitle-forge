# PLAN — Phase 5: Externalize Prompts to settings.yaml

## Goal
Move all hardcoded LLM prompts from Python source files into `settings.yaml`, making them configurable per domain without editing code.

## Done Criteria
- 5 prompts moved from source code to `settings.yaml` under `prompts:` key
- `config.py` has `DOMAIN` and loads all prompts
- All callers use `config.PROMPT_*` instead of hardcoded strings
- `{domain}` placeholder replaces "CFA" in prompts
- 25 tests pass, all imports work

## Tasks

| # | Task | Est. | Files |
|---|------|------|-------|
| 1 | Add `domain` + `prompts` to settings.yaml | 5 min | settings.yaml |
| 2 | Add DOMAIN + prompt constants to config.py | 10 min | config.py |
| 3 | Update translator.py → use config prompt | 5 min | translator.py |
| 4 | Update notes_generator.py → use config prompt | 5 min | notes_generator.py |
| 5 | Update chapter_generator.py → use config prompt | 5 min | chapter_generator.py |
| 6 | Update qa_agent.py → use config prompt | 5 min | qa_agent.py |
| 7 | Update glossary_manager.py → use config prompt | 5 min | glossary_manager.py |
| 8 | Verify: pytest + import check | 5 min | — |
