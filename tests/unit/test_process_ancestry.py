from __future__ import annotations

import json

import pytest

from agentic_conformance.process_ancestry import (
    ProcessAncestry,
    ProcessNode,
    assess_worker_neutrality,
    parse_process_table,
    sanitized_environment,
)


def test_parses_windows_process_table_and_builds_ordered_ancestry() -> None:
    raw = json.dumps(
        [
            {
                "ProcessId": 400,
                "ParentProcessId": 300,
                "Name": "python.exe",
                "ExecutablePath": "C:/Python/python.exe",
            },
            {
                "ProcessId": 300,
                "ParentProcessId": 200,
                "Name": "taskeng.exe",
                "ExecutablePath": "C:/Windows/taskeng.exe",
            },
            {
                "ProcessId": 200,
                "ParentProcessId": 4,
                "Name": "svchost.exe",
                "ExecutablePath": "C:/Windows/svchost.exe",
            },
            {"ProcessId": 4, "ParentProcessId": 0, "Name": "System", "ExecutablePath": None},
        ]
    )

    table = parse_process_table(raw)
    ancestry = ProcessAncestry.from_processes(400, table, "2026-08-28T12:00:00Z")

    assert [node.pid for node in ancestry.nodes] == [400, 300, 200, 4]
    assert ancestry.complete is True
    assert ancestry.cycle_detected is False
    assert ancestry.to_mapping()["nodes"][1] == {
        "pid": 300,
        "parent_pid": 200,
        "name": "taskeng.exe",
        "executable": "C:/Windows/taskeng.exe",
    }


def test_neutrality_requires_scheduler_and_rejects_agent_ancestor() -> None:
    neutral = ProcessAncestry(
        subject_pid=400,
        nodes=(
            ProcessNode(400, 300, "python.exe", "C:/Python/python.exe"),
            ProcessNode(300, 200, "taskeng.exe", "C:/Windows/taskeng.exe"),
            ProcessNode(200, 4, "svchost.exe", "C:/Windows/svchost.exe"),
        ),
        captured_at="2026-08-28T12:00:00Z",
        complete=False,
        cycle_detected=False,
    )
    assert assess_worker_neutrality(neutral).valid

    nested = ProcessAncestry(
        subject_pid=400,
        nodes=(
            ProcessNode(400, 350, "python.exe", "C:/Python/python.exe"),
            ProcessNode(350, 300, "codex.exe", "C:/tools/codex.exe"),
            ProcessNode(300, 200, "taskeng.exe", "C:/Windows/taskeng.exe"),
        ),
        captured_at=neutral.captured_at,
        complete=False,
        cycle_detected=False,
    )
    decision = assess_worker_neutrality(nested)
    assert not decision.valid
    assert decision.status == "INVALID_NEUTRAL_ENVIRONMENT"
    assert "coding-agent ancestor" in decision.reason

    unscheduled = ProcessAncestry(
        subject_pid=400,
        nodes=(
            ProcessNode(400, 300, "python.exe", None),
            ProcessNode(300, 0, "explorer.exe", None),
        ),
        captured_at=neutral.captured_at,
        complete=True,
        cycle_detected=False,
    )
    assert not assess_worker_neutrality(unscheduled).valid
    assert "scheduler" in assess_worker_neutrality(unscheduled).reason


def test_cycle_or_missing_subject_fails_closed() -> None:
    cycle = ProcessAncestry.from_processes(
        10,
        (ProcessNode(10, 20, "python.exe", None), ProcessNode(20, 10, "taskeng.exe", None)),
        "2026-08-28T12:00:00Z",
    )
    assert cycle.cycle_detected
    assert not assess_worker_neutrality(cycle).valid

    with pytest.raises(ValueError, match="subject"):
        ProcessAncestry.from_processes(99, (), "2026-08-28T12:00:00Z")


def test_malformed_process_table_is_rejected() -> None:
    with pytest.raises(ValueError, match="JSON"):
        parse_process_table("not-json")
    with pytest.raises(ValueError, match="fields"):
        parse_process_table('[{"ProcessId":"bad"}]')


def test_sanitized_environment_is_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret")
    monkeypatch.setenv("COOKIE", "secret")

    envelope = sanitized_environment()
    serialized = json.dumps(envelope).casefold()

    assert set(envelope) == {
        "os",
        "os_release",
        "python",
        "python_implementation",
        "machine",
    }
    assert "secret" not in serialized
    assert "token" not in serialized
    assert "cookie" not in serialized
    assert "key" not in serialized
