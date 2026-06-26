"""Smoke tests for WorkflowEngine — TDD safety net for director.py refactoring."""
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def test_workflow_engine_can_instantiate():
    """WorkflowEngine loads multi_agent_workflow.json and parses agents."""
    from director import WorkflowEngine

    workflow_path = PROJECT_ROOT / "multi_agent_workflow.json"
    assert workflow_path.exists(), f"Workflow file not found: {workflow_path}"

    engine = WorkflowEngine(workflow_path)
    assert len(engine.agents) > 0, "Expected at least 1 agent in workflow"
    assert engine.agent_map, "agent_map should not be empty"


def test_workflow_engine_parses_agent_fields():
    """Each agent has required fields populated."""
    from director import WorkflowEngine, AgentConfig

    workflow_path = PROJECT_ROOT / "multi_agent_workflow.json"
    engine = WorkflowEngine(workflow_path)

    for agent in engine.agents:
        assert isinstance(agent, AgentConfig)
        assert agent.id, f"Agent missing id: {agent}"
        assert agent.action, f"Agent {agent.id} missing action"
        assert isinstance(agent.dependencies, list)


def test_workflow_engine_load_all_agents():
    """Verify total agent count matches the workflow JSON."""
    from director import WorkflowEngine

    workflow_path = PROJECT_ROOT / "multi_agent_workflow.json"
    data = json.loads(workflow_path.read_text(encoding="utf-8"))

    engine = WorkflowEngine(workflow_path)
    assert len(engine.agents) == len(data["agents"]), (
        f"Engine parsed {len(engine.agents)} agents, "
        f"expected {len(data['agents'])}"
    )
