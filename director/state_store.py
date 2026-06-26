"""State persistence for the Multi-Agent Orchestration Engine.

Manages reading and writing state.json in each video's working directory.
"""
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


class StateStore:
    """Manages persistence of agent states in the working directory."""

    def __init__(self, working_dir: Path):
        self.path = working_dir / "state.json"
        self.working_dir = working_dir
        self.lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"agents": {}, "outputs": {}}

    def save(self):
        with self.lock:
            self.path.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def get_agent_status(self, agent_id: str) -> str:
        return self.data["agents"].get(agent_id, {}).get("status", "PENDING")

    def set_agent_status(self, agent_id: str, status: str, error: Optional[str] = None):
        if agent_id not in self.data["agents"]:
            self.data["agents"][agent_id] = {}
        self.data["agents"][agent_id]["status"] = status
        self.data["agents"][agent_id]["timestamp"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if error:
            self.data["agents"][agent_id]["error"] = error
        elif status in ["RUNNING", "COMPLETED"]:
            self.data["agents"][agent_id].pop("error", None)
        self.save()

    def update_outputs(self, outputs: Dict[str, Any]):
        def serialize(v):
            if isinstance(v, (list, tuple)):
                return [serialize(i) for i in v]
            if isinstance(v, dict):
                return {k: serialize(val) for k, val in v.items()}
            if isinstance(v, Path):
                return str(v)
            return v

        self.data["outputs"].update(
            {k: serialize(v) for k, v in outputs.items()}
        )
        self.save()

    def get_output(self, key: str) -> Any:
        if key in self.data["outputs"]:
            return self.data["outputs"][key]
        if key == "working_directory":
            return str(self.working_dir)
        return None
