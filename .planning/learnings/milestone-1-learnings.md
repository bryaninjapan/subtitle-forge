# Learnings: Milestone 1 — Codebase Health + Module Refactoring

Date: 2026-06-26
Commits: 18

## What Worked Well

### 1. TDD Smoke Test Before Refactoring
Writing `test_director.py` (3 smoke tests) **before** splitting director.py caught no regressions during the split. The tests verified constructor + agent parsing, which is the most brittle part of a DAG engine refactor.

→ **Apply to future:** Always write a smoke test for the module being refactored before touching it.

### 2. Spike-First for Mechanical Changes
CFA hardcoding survey (spike 003) and unused imports (spike 002) followed the pattern: scan → validate → report → decide. This prevented wasted effort on unnecessary changes (e.g. print vs console was flagged by scan but determined to be non-issue after reading actual code).

→ **Apply to future:** Scans are directional, not authoritative. Always read the actual code before treating scan results as requirements.

### 3. `delegate_task` vs `gsd-autonomous`
Simple mechanical splits (director.py, srt_utils, media_utils) were best done inline with patch/write_file. OpenCode dispatch was not needed because changes were pure code movement with no behavioral ambiguity.

→ **Apply to future:** Use inline edits for code movement; delegate_task for reasoning-heavy tasks (research, comparison).

### 4. Externalizing Prompts to Config
Moving 6 hardcoded prompts from source code to settings.yaml was a 30-min task with zero behavioral change. The `{domain}` placeholder pattern makes cross-domain support trivial.

→ **Apply to future:** Config-driven prompts should be the default pattern from project start.

## Pitfalls Encountered

### 1. Scan Report Was Wrong About print vs Console
The initial codebase scan claimed `asr_engine.py uses print(), other modules use rich.console`. Reality: **18 files use print(), only 3 use Console** — the exact opposite.

→ **Fix:** Never trust automated scan reports as design requirements. Spot-check with `grep` before making decisions.

### 2. Patch Failed on Multi-Line Strings
Replacing a 15-line hardcoded prompt string in `notes_generator.py` failed on the first attempt because the indentation in `old_string` didn't match the file exactly (inner indentation used 4 spaces vs file had exact alignment).

→ **Fix:** Use `read_file` + exact copy-paste from the file for multi-line old_string, or use `write_file` for the entire block.

### 3. Verification Script Regex Over-Matched `store.data`
The ad-hoc verification script for StateStore tests flagged `assert store.data[...] == ...` as "direct mutation", but those lines were **reads** (assertions), not **writes**. The `==` in assertions was confused with assignment `=`.

→ **Fix:** Verification scripts need `==` exclusion logic or use AST parsing instead of regex.

### 4. Spike Branch Deletion Lost Commits
When force-deleting `spike/survey-cfa-hardcoding`, the commit containing the spike report was lost because it had never been merged. The report had to be re-created on `feature/local-asr-qwen3`.

→ **Fix:** Before deleting a spike branch, check if it has unmerged commits the user wants to keep. Either merge the report file or cherry-pick the commit.

## Surprises

### 1. `burn_subtitles` Was Dead Code
During media_utils splitting, `burn_subtitles()` was defined but never imported or called anywhere in the codebase. The function existed purely as dead code.

→ **Action:** Keep the extracted `srt_burn.py` module but deprecate it, or remove it entirely.

### 2. `.env` Manual Parsing Was Identical Copy-Paste
Both `gemini_client.py` and `openrouter_client.py` had identical 8-line manual `.env` parsing blocks. The exact same code pasted twice.

→ **Action:** This pattern confirms the value of centralising shared infrastructure in config.py.

## Improvements for Next Time

| # | Improvement | Why |
|---|-------------|-----|
| 1 | Run verification script **before** reverting spike changes | Ensures clean evidence even if branch is lost |
| 2 | Use `read_file` + exact copy for multi-line patches | Avoids indentation mismatch failures |
| 3 | AST parsing for verification instead of regex | Avoids false positives on `==` vs `=` |
| 4 | Smaller, more frequent commits | Makes rollback easier (today's 18 commits were good) |

## Reusable Patterns

### Prompt Externalization Pattern
```python
# settings.yaml
domain: "CFA"
prompts:
  my_prompt: "You are a {domain} expert..."

# config.py
DOMAIN = _cfg.get("domain", "CFA")
_prompts_c = _cfg.get("prompts", {})
MY_PROMPT = _prompts_c.get("my_prompt", "").replace("{domain}", DOMAIN)
```

### TDD Safety Net for Refactoring
1. Write smoke test on current code (GREEN)
2. Refactor
3. Verify same test still passes (GREEN)
4. If it fails, you broke something

### StateStore Test Pattern
- Test through public API only (no direct `store.data` writes)
- Test persistence roundtrip: write → reload → verify
- Test edge cases: corrupted JSON, empty file, concurrent access
