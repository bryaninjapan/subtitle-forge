# PLAN — Phase 3.1: Split director.py into modules

## Goal
Refactor `director.py` (575 lines) into a `director/` package with clear module boundaries, improving testability and maintainability.

## Done Criteria
- `director.py` no longer exists as a single file; replaced by `director/` package
- `from director import WorkflowEngine` still works (backward compatible)
- All existing functionality preserved
- Tests 3/3 PASSED

## Tasks

| # | Task | Est. | Dependencies |
|---|------|------|-------------|
| 0 | Write smoke test for WorkflowEngine (TDD safety net) | 10 min | — |
| 1 | Create `director/state_store.py` with `StateStore` class | 15 min | — |
| 2 | Create `director/engine.py` with `WorkflowEngine` + `AgentConfig` | 30 min | 1 |
| 3 | Create `director/__init__.py` for public exports | 5 min | 2 |
| 4 | Thin `director.py` → keep only `main()` CLI entry | 10 min | 3 |
| 5 | Verify imports + run tests | 10 min | 4 |

## Task Details

### Task 0 — Write smoke test for WorkflowEngine
- Create `tests/test_director.py`
- Test that `WorkflowEngine` can instantiate with the real `multi_agent_workflow.json`
- Test that `len(engine.agents) > 0` (agents are parsed)
- Verify it's GREEN on the current `director.py` before any refactoring
- This becomes the safety net for the rest of the split

### Task 1 — Create `director/state_store.py`
- Move `StateStore` class as-is
- Add necessary imports (`json`, `threading`, `Path`, `typing`)
- Keep all methods identical: `_load`, `save`, `get_agent_status`, `set_agent_status`, `update_outputs`, `get_output`

### Task 2 — Create `director/engine.py`
- Move `WorkflowEngine` class
- Move `AgentConfig` dataclass
- Move module-level constants: `MAX_CROSS_SESSION_RETRIES`, `_PERMANENT_ERROR_SIGNALS`, `_is_permanent_error()`
- Import `StateStore` from `director.state_store`
- Keep `console = Console()` at module level
- All methods: `__init__`, `_load_workflow`, `_bootstrap_from_disk`, `process_video`, `execute_agent`, `_dispatch_action`, `_print_qa_summary`, `_print_review_queue`, `run_all`

### Task 3 — Create `director/__init__.py`
```python
from .engine import WorkflowEngine, AgentConfig
```
This ensures `from director import WorkflowEngine` still works.

### Task 4 — Thin `director.py`
- Delete all classes and `console = Console()`
- Keep only `main()` function and `if __name__ == "__main__": main()`
- Add `from director.engine import WorkflowEngine` (for `main()`)
- Add `from config import BASE_DIR, INPUT_DIR` (for `main()`)
- Add `from asr_engine import is_media_file` (for `main()`)

### Task 5 — Verify
- `python3 -c "from director import WorkflowEngine"`
- `python3 -c "from director.state_store import StateStore"`
- `python3 -m pytest -v`
- `git diff --stat`

## Not in scope
- Splitting `_bootstrap_from_disk` out of `WorkflowEngine` (future)
- Splitting `_dispatch_action` out (future)
- Adding new tests (separate phase)
- Any behavioral changes

## Rollback
If tests fail, `git checkout -- director/ director.py` restores everything.
