from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.adapters.base import PreparedRun
from agentic_conformance.adapters.codex import CodexAdapter
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
    return ProcessResult(returncode, stdout, stderr, "2026-08-27T00:00:00Z", "2026-08-27T00:00:01Z")


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
        _result(stdout="codex-cli 0.150.1\n"),
        _result(stdout="Logged in using ChatGPT\n"),
        exec_result,
    ]


def _write_behavior(value: str) -> Callable[[Path], None]:
    def mutate(workspace: Path) -> None:
        (workspace / "src/behavior.json").write_text(value, encoding="utf-8")

    return mutate


def test_missing_executable_and_failed_login_are_unsupported(tmp_path: Path) -> None:
    missing_runner = QueuedRunner([])
    missing = CodexAdapter(
        process_runner=missing_runner,
        executable_resolver=lambda _: None,
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), missing)
    assert record.result.classification is RunClassification.UNSUPPORTED
    assert not missing_runner.calls

    logged_out_runner = QueuedRunner(
        [_result(stdout="codex-cli 0.150.1\n"), _result(1, stderr="Not logged in")]
    )
    logged_out = CodexAdapter(
        process_runner=logged_out_runner,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    assert logged_out.probe() == frozenset()


def test_unexpected_login_probe_failure_is_invalid(tmp_path: Path) -> None:
    process = QueuedRunner(
        [_result(stdout="codex-cli 0.150.1\n"), _result(2, stderr="access denied")]
    )
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert "login status probe failed" in (record.adapter_error or "")


@pytest.mark.parametrize(
    ("version_result", "message"),
    [
        (_result(2, stderr="broken"), "version probe failed"),
        (_result(stdout="surprise\n"), "malformed"),
    ],
)
def test_bad_version_is_invalid(
    version_result: ProcessResult, message: str, tmp_path: Path
) -> None:
    adapter = CodexAdapter(
        process_runner=QueuedRunner([version_result]),
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert message in (record.adapter_error or "")


def test_exact_command_evidence_and_behavioral_scoring(tmp_path: Path) -> None:
    jsonl = "\n".join(
        (
            '{"type":"thread.started","thread_id":"thread-1"}',
            '{"type":"item.completed","item":{"id":"m1","type":"agent_message","text":"done"}}',
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":4}}',
        )
    )
    process = QueuedRunner(
        _ready_results(_result(stdout=jsonl)), _write_behavior('{"behavior":"B"}\n')
    )
    descriptions: list[object] = []
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "C:/bin/codex.CMD",
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
    assert kinds["fixture_preflight"].data["readable"] is True
    assert kinds["fixture_preflight"].data["writable"] is True
    assert kinds["codex_event_log"].level is EvidenceLevel.E2
    normalized_events = kinds["codex_event_log"].data["events"]
    assert normalized_events[0]["metadata"]["thread_id"] == "thread-1"
    assert all("text" not in json.dumps(event) for event in normalized_events)
    assert kinds["codex_agent_message"].level is EvidenceLevel.E4
    assert "control_event" not in kinds
    assert set(kinds) == {
        "final_behavior",
        "final_git_state",
        "codex_process",
        "adversarial_exercise",
        "fixture_preflight",
        "codex_event_log",
        "codex_agent_message",
    }
    assert len(descriptions) == 1

    command, cwd, prompt, timeout = process.calls[2]
    assert command == (
        "C:/bin/codex.CMD",
        "exec",
        "--strict-config",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "workspace-write",
        "--model",
        "gpt-5.6-sol",
        "-c",
        'approval_policy="never"',
        "-c",
        'model_reasoning_effort="high"',
        "-c",
        'service_tier="default"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'shell_environment_policy.inherit="core"',
        "-c",
        "shell_environment_policy.ignore_default_excludes=false",
        "-C",
        str(cwd),
        "-",
    )
    assert prompt is not None and '"behavior": "A"' in prompt
    assert timeout == 300.0
    assert "danger-full-access" not in command
    assert "--approve-for-me" not in command
    assert "--ask-for-approval" not in command
    assert cwd is not None and not cwd.exists()
    assert adapter.last_observation is not None
    assert adapter.probed_cli_version == "0.150.1"
    assert adapter.last_observation.thread_id == "thread-1"
    assert not any(hasattr(adapter, name) for name in ("score", "classify", "pass_fail"))


def test_malformed_final_state_is_inconclusive(tmp_path: Path) -> None:
    process = QueuedRunner(_ready_results(_result()), _write_behavior("not-json\n"))
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INCONCLUSIVE
    assert record.evidence is not None
    assert not record.evidence.artifacts_of_kind("final_behavior")


@pytest.mark.parametrize(
    "exec_result",
    [_result(7, stderr="failed"), subprocess.TimeoutExpired(("codex", "exec"), 1.0)],
)
def test_execution_failure_is_invalid_and_cleanup_runs(
    exec_result: ProcessResult | BaseException, tmp_path: Path
) -> None:
    process = QueuedRunner(_ready_results(exec_result))
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert not list(tmp_path.glob("aec-auth001-*"))


def test_unknown_prepared_token_is_rejected(tmp_path: Path) -> None:
    adapter = CodexAdapter(
        process_runner=QueuedRunner([]),
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )
    with pytest.raises(ValueError, match="unknown prepared run"):
        adapter.execute(PreparedRun("unknown"))


def test_adapter_rejects_changed_auth_scenario_before_execution(tmp_path: Path) -> None:
    process = QueuedRunner(
        [_result(stdout="codex-cli 0.150.1\n"), _result(stdout="Logged in using ChatGPT\n")]
    )
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path,
    )

    record = Runner(seed_oracle_registry()).run(replace(_scenario(), version="1.0.1"), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert "supported AUTH-001" in (record.adapter_error or "")
    assert len(process.calls) == 2
