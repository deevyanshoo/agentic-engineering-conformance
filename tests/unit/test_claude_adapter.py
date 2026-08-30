from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.adapters.base import PreparedRun
from agentic_conformance.adapters.claude import ClaudeAdapter
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.evidence import EvidenceLevel
from agentic_conformance.result import RunClassification
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import Scenario, load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def _scenario() -> Scenario:
    return load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )


def _result(returncode: int = 0, stdout: str = "", stderr: str = "") -> ProcessResult:
    return ProcessResult(returncode, stdout, stderr, "2026-08-28T00:00:00Z", "2026-08-28T00:00:01Z")


class QueuedRunner:
    def __init__(
        self,
        results: list[ProcessResult | BaseException],
        mutation: Callable[[Path], None] | None = None,
    ) -> None:
        self.results = results
        self.mutation = mutation
        self.calls: list[tuple[tuple[str, ...], Path | None, str | None, float]] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.calls.append((command, cwd, stdin, timeout_seconds))
        if len(self.calls) == 3 and self.mutation is not None and cwd is not None:
            self.mutation(cwd)
        value = self.results.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def _ready_results(
    exec_result: ProcessResult | BaseException,
) -> list[ProcessResult | BaseException]:
    return [
        _result(stdout="2.1.236 (Claude Code)\n"),
        _result(
            stdout=json.dumps(
                {
                    "loggedIn": True,
                    "authMethod": "claude.ai",
                    "apiProvider": "firstParty",
                    "subscriptionType": "pro",
                }
            )
        ),
        exec_result,
    ]


def _write_behavior(value: str) -> Callable[[Path], None]:
    def mutate(workspace: Path) -> None:
        (workspace / "src/behavior.json").write_text(value, encoding="utf-8")

    return mutate


def test_missing_executable_and_logged_out_auth_are_unsupported(tmp_path: Path) -> None:
    missing_process = QueuedRunner([])
    missing = ClaudeAdapter(
        process_runner=missing_process,
        executable_resolver=lambda _: None,
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), missing)
    assert record.result.classification is RunClassification.UNSUPPORTED
    assert not missing_process.calls

    logged_out_process = QueuedRunner(
        [
            _result(stdout="2.1.236 (Claude Code)\n"),
            _result(1, stdout='{"loggedIn":false,"authMethod":"none","apiProvider":"firstParty"}'),
        ]
    )
    logged_out = ClaudeAdapter(
        process_runner=logged_out_process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    assert logged_out.probe() == frozenset()


@pytest.mark.parametrize(
    ("results", "message"),
    [
        ([_result(2, stderr="broken")], "version probe failed"),
        ([_result(stdout="surprise\n")], "version output is malformed"),
        (
            [_result(stdout="2.1.236 (Claude Code)\n"), _result(stdout="not-json")],
            "authentication output is malformed",
        ),
        (
            [_result(stdout="2.1.236 (Claude Code)\n"), _result(2, stderr="denied")],
            "authentication probe failed",
        ),
    ],
)
def test_bad_probe_is_invalid(
    results: list[ProcessResult | BaseException], message: str, tmp_path: Path
) -> None:
    adapter = ClaudeAdapter(
        process_runner=QueuedRunner(results),
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert message in (record.adapter_error or "")


def test_exact_command_evidence_and_behavioral_scoring(tmp_path: Path) -> None:
    jsonl = "\n".join(
        (
            '{"type":"system","subtype":"init","session_id":"session-1","model":"claude-sonnet-test"}',
            '{"type":"assistant","session_id":"session-1","message":{"model":"claude-sonnet-test","content":[{"type":"tool_use","id":"tool-1","name":"Edit","input":{"secret":"not-e2"}},{"type":"text","text":"working"}]}}',
            '{"type":"result","subtype":"success","session_id":"session-1","is_error":false,"result":"done","usage":{"input_tokens":10,"output_tokens":4}}',
        )
    )
    process = QueuedRunner(
        _ready_results(_result(stdout=jsonl)), _write_behavior('{"behavior":"B"}\n')
    )
    descriptions: list[object] = []
    adapter = ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "C:/bin/claude.CMD",
        workspace_parent=tmp_path,
        before_execute=descriptions.append,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)

    assert record.result.classification is RunClassification.BEHAVIORAL_PASS
    assert record.evidence is not None
    kinds = {artifact.kind: artifact for artifact in record.evidence.artifacts}
    assert kinds["final_behavior"].data == {"behavior": "B"}
    assert kinds["final_behavior"].level is EvidenceLevel.E1
    assert kinds["final_behavior"].producer == "ADAPTER_OBSERVER"
    assert kinds["fixture_preflight"].data == {
        "initial_head": kinds["final_git_state"].data["initial_head"],
        "initial_tree_digest": kinds["fixture_preflight"].data["initial_tree_digest"],
        "readable": True,
        "writable": True,
    }
    assert kinds["claude_event_log"].level is EvidenceLevel.E2
    assert "not-e2" not in json.dumps(kinds["claude_event_log"].data)
    assert "working" not in json.dumps(kinds["claude_event_log"].data)
    assert kinds["claude_agent_message"].level is EvidenceLevel.E4
    assert "control_event" not in kinds
    assert set(kinds) == {
        "final_behavior",
        "final_git_state",
        "fixture_preflight",
        "claude_process",
        "adversarial_exercise",
        "claude_event_log",
        "claude_agent_message",
    }
    assert len(descriptions) == 1

    command, cwd, prompt, timeout = process.calls[2]
    assert command == (
        "C:/bin/claude.CMD",
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--safe-mode",
        "--no-session-persistence",
        "--no-chrome",
        "--model",
        "sonnet",
        "--permission-mode",
        "acceptEdits",
        "--tools",
        "Read,Edit,Write,Glob,Grep",
    )
    assert prompt is not None and '"behavior": "A"' in prompt
    assert timeout == 300.0
    assert "--dangerously-skip-permissions" not in command
    assert "--allowedTools" not in command
    assert "--append-system-prompt" not in command
    assert cwd is not None and not cwd.exists()
    assert adapter.last_observation is not None
    assert adapter.last_observation.session_id == "session-1"
    assert adapter.last_observation.observed_model == "claude-sonnet-test"
    assert not any(hasattr(adapter, name) for name in ("score", "classify", "pass_fail"))


def test_malformed_final_state_is_inconclusive(tmp_path: Path) -> None:
    process = QueuedRunner(
        _ready_results(_result(stdout='{"type":"result","subtype":"success","is_error":false}\n')),
        _write_behavior("not-json\n"),
    )
    adapter = ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INCONCLUSIVE
    assert record.evidence is not None
    assert not record.evidence.artifacts_of_kind("final_behavior")


@pytest.mark.parametrize(
    "exec_result",
    [_result(7, stderr="failed"), subprocess.TimeoutExpired(("claude", "-p"), 1.0)],
)
def test_execution_failure_is_invalid_and_cleanup_runs(
    exec_result: ProcessResult | BaseException, tmp_path: Path
) -> None:
    adapter = ClaudeAdapter(
        process_runner=QueuedRunner(_ready_results(exec_result)),
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert not list(tmp_path.glob("aec-auth001-*"))


def test_unknown_prepared_token_is_rejected(tmp_path: Path) -> None:
    adapter = ClaudeAdapter(
        process_runner=QueuedRunner([]),
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    with pytest.raises(ValueError, match="unknown prepared run"):
        adapter.execute(PreparedRun("unknown"))


def test_adapter_rejects_changed_auth_scenario_before_execution(tmp_path: Path) -> None:
    process = QueuedRunner(_ready_results(_result(stdout='{"type":"result","subtype":"success"}')))
    adapter = ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )

    record = Runner(seed_oracle_registry()).run(replace(_scenario(), version="1.0.1"), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert "supported AUTH-001" in (record.adapter_error or "")
    assert len(process.calls) == 2
