from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.adapters.auth_fixture import auth_fixture_digest
from agentic_conformance.adapters.claude import ClaudeAdapter, ClaudeRunDescription
from agentic_conformance.adapters.codex import CodexAdapter, CodexRunDescription
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.claude_trial import claude_config_digest
from agentic_conformance.codex_trial import codex_config_digest
from agentic_conformance.experiment_plan import HostBinding, build_auth_plan, write_plan
from agentic_conformance.experiment_worker import HostRuntime, run_experiment
from agentic_conformance.process_ancestry import ProcessAncestry, ProcessNode
from agentic_conformance.result import RunClassification
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import load_scenario

ROOT = Path(__file__).parents[2]


class HostProcess:
    def __init__(
        self,
        host: str,
        *,
        available: bool = True,
        auth_mode: str | None = None,
        fail_execution: bool = False,
    ) -> None:
        self.host = host
        self.available = available
        self.auth_mode = auth_mode
        self.fail_execution = fail_execution
        self.execution_calls = 0
        self.observations: list[dict[str, object]] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del stdin, timeout_seconds
        if command[-1] == "--version":
            stdout = "codex-cli 0.150.1\n" if self.host == "codex" else "2.1.236 (Claude Code)\n"
            return _result(stdout=stdout)
        if self.host == "codex" and command[-2:] == ("login", "status"):
            return _result(
                0 if self.available else 1,
                stdout=(
                    f"Logged in using {self.auth_mode or 'ChatGPT'}\n"
                    if self.available
                    else "Not logged in\n"
                ),
            )
        if self.host == "claude" and command[-3:] == ("auth", "status", "--json"):
            return _result(
                0 if self.available else 1,
                stdout=json.dumps(
                    {
                        "loggedIn": self.available,
                        "authMethod": "claude.ai" if self.available else "none",
                        "apiProvider": "firstParty",
                        "subscriptionType": "pro" if self.available else None,
                    }
                ),
            )
        self.execution_calls += 1
        self.observations.append(
            {
                "pid": 500 + self.execution_calls,
                "command": list(command),
                "ancestry": _neutral_ancestry(500 + self.execution_calls).to_mapping(),
                "timed_out": False,
            }
        )
        if self.fail_execution:
            return _result(7, stderr="synthetic host failure")
        assert cwd is not None
        (cwd / "src/behavior.json").write_text('{"behavior":"B"}\n', encoding="utf-8")
        if self.host == "codex":
            return _result(
                stdout=(
                    '{"type":"thread.started","thread_id":"neutral-codex"}\n'
                    '{"type":"turn.completed","usage":{"output_tokens":1}}\n'
                )
            )
        return _result(
            stdout=(
                '{"type":"system","subtype":"init","session_id":"neutral-claude","model":"claude-sonnet-test"}\n'
                '{"type":"result","subtype":"success","session_id":"neutral-claude","is_error":false,"result":"done"}\n'
            )
        )


def _result(returncode: int = 0, stdout: str = "", stderr: str = "") -> ProcessResult:
    return ProcessResult(returncode, stdout, stderr, "2026-08-28T12:00:00Z", "2026-08-28T12:00:01Z")


def _neutral_ancestry(pid: int) -> ProcessAncestry:
    return ProcessAncestry(
        pid,
        (
            ProcessNode(pid, 300, "python.exe", "C:/Python/python.exe"),
            ProcessNode(300, 200, "taskeng.exe", "C:/Windows/taskeng.exe"),
            ProcessNode(200, 0, "svchost.exe", "C:/Windows/svchost.exe"),
        ),
        "2026-08-28T12:00:00Z",
        True,
        False,
    )


def _nested_ancestry(pid: int) -> ProcessAncestry:
    return ProcessAncestry(
        pid,
        (
            ProcessNode(pid, 300, "python.exe", "C:/Python/python.exe"),
            ProcessNode(300, 0, "codex.exe", "C:/tools/codex.exe"),
        ),
        "2026-08-28T12:00:00Z",
        True,
        False,
    )


def _copy_contract(source_root: Path) -> tuple[str, str]:
    scenario_target = source_root / "scenarios/authority/AUTH-001/scenario.json"
    schema_target = source_root / "schemas/scenario.schema.json"
    scenario_target.parent.mkdir(parents=True)
    schema_target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scenarios/authority/AUTH-001/scenario.json", scenario_target)
    shutil.copyfile(ROOT / "schemas/scenario.schema.json", schema_target)
    fixture_target = source_root / "fixtures/AUTH-001.json"
    fixture_target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "fixtures/AUTH-001.json", fixture_target)
    scenario = load_scenario(scenario_target, schema_target)
    return scenario.version, scenario_digest(scenario)


def _bindings() -> tuple[HostBinding, HostBinding]:
    workspace = Path("C:/fixture")
    codex_description = CodexRunDescription(
        "0.150.1",
        (),
        workspace,
        "gpt-5.6-sol",
        "high",
        "default",
        "workspace-write",
        False,
        True,
        True,
    )
    claude_description = ClaudeRunDescription(
        "2.1.236",
        (),
        workspace,
        "sonnet",
        "stream-json",
        "acceptEdits",
        ("Read", "Edit", "Write", "Glob", "Grep"),
        True,
        False,
        False,
        False,
        True,
        False,
    )
    return (
        HostBinding(
            "codex",
            "0.2.0",
            "0.150.1",
            "C:/tools/codex.CMD",
            "gpt-5.6-sol",
            codex_config_digest(codex_description),
            "workspace-write;network=false",
            "chatgpt",
            "openai",
            None,
        ),
        HostBinding(
            "claude",
            "0.3.0",
            "2.1.236",
            "C:/tools/claude.CMD",
            "sonnet",
            claude_config_digest(claude_description),
            "safe-mode;no-shell;no-web",
            "claude.ai",
            "firstParty",
            "pro",
        ),
    )


def _plan(tmp_path: Path):
    source_root = (tmp_path / "source").resolve()
    version, digest = _copy_contract(source_root)
    codex, claude = _bindings()
    return build_auth_plan(
        batch_id="m4-neutral-worker",
        benchmark_revision="a" * 40,
        source_root=source_root,
        output_root=(source_root / "reports/runs/m4-neutral-worker").resolve(),
        scenario_version=version,
        scenario_digest=digest,
        fixture_version="1.0.0",
        fixture_digest=auth_fixture_digest(),
        codex=codex,
        claude=claude,
        created_at="2026-08-28T12:00:00Z",
    )


def _factory(
    processes: dict[str, HostProcess],
) -> Callable[[HostBinding, Path, Callable[[object], None]], HostRuntime]:
    def create(
        binding: HostBinding, workspace_parent: Path, before_execute: Callable[[object], None]
    ) -> HostRuntime:
        process = processes[binding.name]
        if binding.name == "codex":
            adapter = CodexAdapter(
                process_runner=process,
                executable_resolver=lambda _: binding.executable,
                workspace_parent=workspace_parent,
                before_execute=before_execute,
            )
        else:
            adapter = ClaudeAdapter(
                process_runner=process,
                executable_resolver=lambda _: binding.executable,
                workspace_parent=workspace_parent,
                before_execute=before_execute,
            )
        return HostRuntime(adapter=adapter, observations=lambda: tuple(process.observations))

    return create


def test_neutral_worker_executes_exactly_six_and_offline_rescores(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {"codex": HostProcess("codex"), "claude": HostProcess("claude")}

    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        runtime_factory=_factory(processes),
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt", "python": "test"},
    )

    assert result.status == "COMPLETE"
    assert result.exit_code == 0
    assert len(result.outcomes) == 6
    assert [outcome.host for outcome in result.outcomes] == [
        "codex",
        "claude",
        "codex",
        "claude",
        "codex",
        "claude",
    ]
    assert processes["codex"].execution_calls == 3
    assert processes["claude"].execution_calls == 3
    assert all(outcome.rescored_equal for outcome in result.outcomes)
    assert all(outcome.classification.value == "BEHAVIORAL_PASS" for outcome in result.outcomes)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["hosts"]["codex"]["scheduled_count"] == 3
    assert summary["hosts"]["claude"]["scheduled_count"] == 3
    marker = json.loads(result.marker_path.read_text(encoding="utf-8"))
    assert marker["status"] == "COMPLETE"
    assert marker["plan_digest"] == plan.plan_digest
    from agentic_conformance.experiment_scheduler import validate_terminal_marker

    assert validate_terminal_marker(plan, marker) == marker
    for outcome in result.outcomes:
        run_dir = plan.output_root / "runs" / outcome.run_id
        assert (run_dir / "evidence.json").exists()
        assert (run_dir / "run.json").exists()
        assert (run_dir / "process-ancestry.json").exists()
        assert (plan.output_root / "outcomes" / f"{outcome.run_id}.json").exists()
    assert all(
        outcome.observed_model_identifier is None
        for outcome in result.outcomes
        if outcome.host == "codex"
    )
    assert {
        outcome.observed_model_identifier for outcome in result.outcomes if outcome.host == "claude"
    } == {"claude-sonnet-test"}


def test_worker_rejects_nested_agent_ancestry_before_host_preflight(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    factory_calls: list[str] = []

    def forbidden_factory(
        binding: HostBinding, workspace_parent: Path, before_execute: Callable[[object], None]
    ) -> HostRuntime:
        del workspace_parent, before_execute
        factory_calls.append(binding.name)
        raise AssertionError("host runtime must not be built in an invalid neutral environment")

    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_nested_ancestry,
        runtime_factory=forbidden_factory,
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt"},
    )

    assert result.status == "INVALID_NEUTRAL_ENVIRONMENT"
    assert result.exit_code != 0
    assert result.outcomes == ()
    assert factory_calls == []
    assert not result.summary_path.exists()


def test_unavailable_host_is_unsupported_without_model_calls(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {
        "codex": HostProcess("codex", available=False),
        "claude": HostProcess("claude"),
    }
    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        runtime_factory=_factory(processes),
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt"},
    )

    codex = [outcome for outcome in result.outcomes if outcome.host == "codex"]
    assert len(codex) == 3
    assert all(outcome.classification.value == "UNSUPPORTED" for outcome in codex)
    assert all(not outcome.attempted for outcome in codex)
    assert all(outcome.requested_model == "gpt-5.6-sol" for outcome in codex)
    assert all(outcome.observed_model_identifier is None for outcome in codex)
    assert processes["codex"].execution_calls == 0
    assert processes["claude"].execution_calls == 3


def test_worker_rejects_recomputed_replacement_plan_against_scheduled_digest(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    changed_codex = replace(
        plan.hosts[0],
        requested_model="different-model",
        config_digest="sha256:" + "9" * 64,
    )
    replacement = replace(
        plan,
        hosts=(changed_codex, plan.hosts[1]),
        plan_digest="",
    ).validated()
    write_plan(plan_path, replacement)

    with pytest.raises(ValueError, match="scheduled digest"):
        run_experiment(
            plan_path,
            plan.plan_digest,
            ancestry_reader=_neutral_ancestry,
            runtime_factory=_factory(
                {"codex": HostProcess("codex"), "claude": HostProcess("claude")}
            ),
            source_state_reader=lambda _: (plan.benchmark_revision, ()),
        )


def test_worker_rejects_available_but_wrong_auth_mode_before_model_call(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {
        "codex": HostProcess("codex", auth_mode="API key"),
        "claude": HostProcess("claude"),
    }

    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        runtime_factory=_factory(processes),
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
    )

    codex = [outcome for outcome in result.outcomes if outcome.host == "codex"]
    assert all(outcome.classification is RunClassification.INVALID_RUN for outcome in codex)
    assert all(outcome.observed_model_identifier is None for outcome in codex)
    assert processes["codex"].execution_calls == 0


def test_failed_host_invocation_retains_process_ancestry_diagnostics(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {
        "codex": HostProcess("codex", fail_execution=True),
        "claude": HostProcess("claude"),
    }

    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        runtime_factory=_factory(processes),
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
    )

    codex = [outcome for outcome in result.outcomes if outcome.host == "codex"]
    assert all(outcome.classification is RunClassification.INVALID_RUN for outcome in codex)
    assert all(outcome.attempted for outcome in codex)
    for outcome in codex:
        ancestry = plan.output_root / "runs" / outcome.run_id / "process-ancestry.json"
        assert ancestry.exists()
        assert json.loads(ancestry.read_text(encoding="utf-8"))["processes"]
