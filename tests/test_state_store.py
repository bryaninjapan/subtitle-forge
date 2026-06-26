"""Unit tests for StateStore — state.json persistence layer."""
import json
import tempfile
from pathlib import Path

import pytest

from director.state_store import StateStore


@pytest.fixture
def tmp_working_dir():
    """Create a temporary directory for each test, cleaned up after."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_init_creates_default_state(tmp_working_dir: Path):
    """StateStore initialises with empty agents and outputs when no state.json exists."""
    store = StateStore(tmp_working_dir)
    assert store.data == {"agents": {}, "outputs": {}}
    assert store.path == tmp_working_dir / "state.json"


def test_init_loads_existing_state(tmp_working_dir: Path):
    """StateStore loads existing state.json on init."""
    state = {"agents": {"a1": {"status": "COMPLETED"}}, "outputs": {"key": "val"}}
    state_path = tmp_working_dir / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    store = StateStore(tmp_working_dir)
    assert store.data == state


def test_init_handles_corrupted_json(tmp_working_dir: Path):
    """StateStore falls back to defaults when state.json is corrupted."""
    state_path = tmp_working_dir / "state.json"
    state_path.write_text("{invalid json", encoding="utf-8")

    store = StateStore(tmp_working_dir)
    assert store.data == {"agents": {}, "outputs": {}}


def test_get_agent_status_defaults_to_pending(tmp_working_dir: Path):
    """Unknown agent returns PENDING status."""
    store = StateStore(tmp_working_dir)
    assert store.get_agent_status("unknown_agent") == "PENDING"


def test_get_agent_status_returns_stored(tmp_working_dir: Path):
    """Status is returned after being set via public API."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("test_agent", "RUNNING")
    assert store.get_agent_status("test_agent") == "RUNNING"


def test_set_agent_status_creates_entry(tmp_working_dir: Path):
    """set_agent_status creates a new agent entry if not exists."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("new_agent", "RUNNING")

    assert store.get_agent_status("new_agent") == "RUNNING"
    assert "timestamp" in store.data["agents"]["new_agent"]


def test_set_agent_status_persists_to_disk(tmp_working_dir: Path):
    """After set_agent_status, the file on disk matches in-memory state."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("agent_x", "COMPLETED")

    reloaded = StateStore(tmp_working_dir)
    assert reloaded.get_agent_status("agent_x") == "COMPLETED"


def test_set_agent_status_clears_error_on_success(tmp_working_dir: Path):
    """Error is cleared when status transitions to COMPLETED from FAILED."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("agent_y", "FAILED", error="something broke")
    assert store.data["agents"]["agent_y"]["error"] == "something broke"

    store.set_agent_status("agent_y", "COMPLETED")
    assert "error" not in store.data["agents"]["agent_y"]


def test_set_agent_status_clears_error_on_running(tmp_working_dir: Path):
    """Error is also cleared when moving to RUNNING."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("agent_z", "FAILED", error="error")
    store.set_agent_status("agent_z", "RUNNING")
    assert "error" not in store.data["agents"]["agent_z"]


def test_set_agent_status_keeps_error_on_other_status(tmp_working_dir: Path):
    """Error is preserved for FAILED statuses."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("agent_w", "FAILED_PERMANENT", error="permanent error")
    assert store.data["agents"]["agent_w"]["error"] == "permanent error"

    # Re-setting FAILED with a new error should keep it
    store.set_agent_status("agent_w", "FAILED", error="new error")
    assert store.data["agents"]["agent_w"]["error"] == "new error"


def test_update_outputs_saves_serializable(tmp_working_dir: Path):
    """update_outputs serialises Path objects to strings."""
    store = StateStore(tmp_working_dir)
    store.update_outputs({"video_path": tmp_working_dir / "test.mp4"})
    assert store.data["outputs"]["video_path"] == str(tmp_working_dir / "test.mp4")


def test_update_outputs_merges_multiple_keys(tmp_working_dir: Path):
    """Multiple calls to update_outputs accumulate keys."""
    store = StateStore(tmp_working_dir)
    store.update_outputs({"key1": "val1"})
    store.update_outputs({"key2": "val2"})
    assert store.data["outputs"]["key1"] == "val1"
    assert store.data["outputs"]["key2"] == "val2"


def test_update_outputs_serialises_nested_lists(tmp_working_dir: Path):
    """Nested Path objects inside lists are serialised."""
    store = StateStore(tmp_working_dir)
    store.update_outputs({"paths": [tmp_working_dir / "a.jpg", tmp_working_dir / "b.jpg"]})
    assert store.data["outputs"]["paths"] == [
        str(tmp_working_dir / "a.jpg"),
        str(tmp_working_dir / "b.jpg"),
    ]


def test_update_outputs_persists_to_disk(tmp_working_dir: Path):
    """Outputs written via update_outputs survive reload."""
    store = StateStore(tmp_working_dir)
    store.update_outputs({"key": "disk_value"})

    reloaded = StateStore(tmp_working_dir)
    assert reloaded.get_output("key") == "disk_value"


def test_get_output_known_key(tmp_working_dir: Path):
    """get_output returns the stored value for an existing key (set via public API)."""
    store = StateStore(tmp_working_dir)
    store.update_outputs({"known": "value"})
    assert store.get_output("known") == "value"


def test_get_output_unknown_key(tmp_working_dir: Path):
    """get_output returns None for a non-existent key."""
    store = StateStore(tmp_working_dir)
    assert store.get_output("nonexistent") is None


def test_get_output_working_directory_special(tmp_working_dir: Path):
    """get_output returns working_dir as string for 'working_directory' key."""
    store = StateStore(tmp_working_dir)
    assert store.get_output("working_directory") == str(tmp_working_dir)


def test_save_writes_valid_json(tmp_working_dir: Path):
    """save() writes a file that can be parsed as JSON (data set via public API)."""
    store = StateStore(tmp_working_dir)
    store.set_agent_status("test", "COMPLETED")
    store.save()

    parsed = json.loads(store.path.read_text(encoding="utf-8"))
    assert parsed["agents"]["test"]["status"] == "COMPLETED"


def test_thread_safety_does_not_crash(tmp_working_dir: Path):
    """Concurrent set/get does not cause obvious race conditions."""
    import concurrent.futures

    store = StateStore(tmp_working_dir)

    def setter(i: int) -> str:
        store.set_agent_status(f"t{i}", "RUNNING")
        return store.get_agent_status(f"t{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(setter, range(20)))

    assert all(r == "RUNNING" for r in results)
    assert len(store.data["agents"]) == 20
