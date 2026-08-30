from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.adapters.auth_fixture import (
    STALE_CONTEXT_PARAGRAPH,
    AuthTreatment,
    auth_fixture_base_digest,
    auth_fixture_digest,
    auth_treatment_digest,
)
from agentic_conformance.adapters.claude import ClaudeAdapter, ClaudeRunDescription
from agentic_conformance.adapters.codex import CodexAdapter, CodexRunDescription
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.claude_trial import claude_config_digest
from agentic_conformance.codex_trial import codex_config_digest
from agentic_conformance.experiment_plan import (
    HostBinding,
    TrialCondition,
    build_auth_plan,
    build_paired_auth_plan,
    write_plan,
)
from agentic_conformance.experiment_worker import (
    HostRuntime,
    default_runtime_factory,
    run_experiment,
)
from agentic_conformance.process_ancestry import ProcessAncestry, ProcessNode
from agentic_conformance.result import RunClassification
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import load_scenario

ROOT = Path(__file__).parents[2]


class HostProcess:
    executes_subprocess = False

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
        self.prompts: list[str] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del timeout_seconds
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
        assert stdin is not None
        self.prompts.append(stdin)
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
    shutil.copyfile(
        ROOT / "scenarios/authority/AUTH-001/scenario-v2.json",
        scenario_target.with_name("scenario-v2.json"),
    )
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


def _paired_plan(tmp_path: Path):
    source_root = (tmp_path / "source").resolve()
    _copy_contract(source_root)
    scenario = load_scenario(
        source_root / "scenarios/authority/AUTH-001/scenario-v2.json",
        source_root / "schemas/scenario.schema.json",
    )
    codex, claude = _bindings()
    return build_paired_auth_plan(
        batch_id="m5-paired-worker",
        benchmark_revision="a" * 40,
        source_root=source_root,
        output_root=(source_root / "reports/runs/m5-paired-worker").resolve(),
        scenario_version=scenario.version,
        scenario_digest=scenario_digest(scenario),
        fixture_version="1.0.0",
        fixture_base_digest=auth_fixture_base_digest(),
        calibration_prompt_digest=auth_treatment_digest(AuthTreatment.CALIBRATION),
        auth_conflict_prompt_digest=auth_treatment_digest(AuthTreatment.AUTH_CONFLICT),
        codex=codex,
        claude=claude,
        created_at="2026-08-29T12:00:00Z",
    )


def _factory(
    processes: dict[str, HostProcess],
) -> Callable[[HostBinding, Path, Callable[[object], None], AuthTreatment], HostRuntime]:
    def create(
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
        treatment: AuthTreatment,
    ) -> HostRuntime:
        process = processes[binding.name]
        if binding.name == "codex":
            adapter = CodexAdapter(
                process_runner=process,
                executable_resolver=lambda _: binding.executable,
                workspace_parent=workspace_parent,
                before_execute=before_execute,
                treatment=treatment,
            )
        else:
            adapter = ClaudeAdapter(
                process_runner=process,
                executable_resolver=lambda _: binding.executable,
                workspace_parent=workspace_parent,
                before_execute=before_execute,
                treatment=treatment,
            )
        return HostRuntime(adapter=adapter, observations=lambda: tuple(process.observations))

    create.executes_subprocess = False
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
        allow_nonlocal_executables_for_testing=True,
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
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
        treatment: AuthTreatment,
    ) -> HostRuntime:
        del workspace_parent, before_execute, treatment
        factory_calls.append(binding.name)
        raise AssertionError("host runtime must not be built in an invalid neutral environment")

    forbidden_factory.executes_subprocess = False
    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_nested_ancestry,
        allow_nonlocal_executables_for_testing=True,
        runtime_factory=forbidden_factory,
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt"},
    )

    assert result.status == "INVALID_NEUTRAL_ENVIRONMENT"
    assert result.exit_code != 0
    assert result.outcomes == ()
    assert factory_calls == []
    assert not result.summary_path.exists()


def test_nonlocal_test_opt_in_never_calls_unmarked_eager_factory(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    calls: list[str] = []

    def eager_factory(
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
        treatment: AuthTreatment,
    ) -> HostRuntime:
        calls.append(binding.name)
        return default_runtime_factory(binding, workspace_parent, before_execute, treatment)

    with pytest.raises(ValueError, match="factory itself"):
        run_experiment(
            plan_path,
            plan.plan_digest,
            ancestry_reader=_neutral_ancestry,
            allow_nonlocal_executables_for_testing=True,
            runtime_factory=eager_factory,
            source_state_reader=lambda _: (plan.benchmark_revision, ()),
        )

    assert calls == []


def test_nonlocal_test_opt_in_rejects_wrapped_subprocess_runtime(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)

    def wrapped_subprocess_factory(
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
        treatment: AuthTreatment,
    ) -> HostRuntime:
        return default_runtime_factory(binding, workspace_parent, before_execute, treatment)

    wrapped_subprocess_factory.executes_subprocess = False
    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        allow_nonlocal_executables_for_testing=True,
        runtime_factory=wrapped_subprocess_factory,
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
    )

    assert all(
        outcome.classification is RunClassification.INVALID_RUN for outcome in result.outcomes
    )
    assert all(not outcome.attempted for outcome in result.outcomes)
    assert all(
        any("non-subprocess runner" in limitation for limitation in outcome.limitations)
        for outcome in result.outcomes
    )


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
        allow_nonlocal_executables_for_testing=True,
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
            allow_nonlocal_executables_for_testing=True,
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
        allow_nonlocal_executables_for_testing=True,
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
        allow_nonlocal_executables_for_testing=True,
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


def test_paired_worker_executes_exactly_twelve_with_distinct_treatments(
    tmp_path: Path,
) -> None:
    plan = _paired_plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {"codex": HostProcess("codex"), "claude": HostProcess("claude")}

    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        allow_nonlocal_executables_for_testing=True,
        runtime_factory=_factory(processes),
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt", "python": "test"},
    )

    assert result.status == "COMPLETE"
    assert len(result.outcomes) == 12
    assert processes["codex"].execution_calls == 6
    assert processes["claude"].execution_calls == 6
    assert all(outcome.rescored_equal for outcome in result.outcomes)
    for process in processes.values():
        assert len(process.prompts) == 6
        assert all(STALE_CONTEXT_PARAGRAPH not in prompt for prompt in process.prompts[0::2])
        assert all(STALE_CONTEXT_PARAGRAPH in prompt for prompt in process.prompts[1::2])
    calibrations = [
        outcome for outcome in result.outcomes if outcome.condition is TrialCondition.CALIBRATION
    ]
    conflicts = [
        outcome for outcome in result.outcomes if outcome.condition is TrialCondition.AUTH_CONFLICT
    ]
    assert {item.calibration_classification.value for item in calibrations} == {"CALIBRATION_PASS"}
    assert all(item.classification.value == "BEHAVIORAL_PASS" for item in conflicts)
    for outcome in calibrations:
        run_dir = plan.output_root / "runs" / outcome.run_id
        assert (run_dir / "calibration.json").exists()
        assert not (run_dir / "run.json").exists()
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["scheduled_total"] == 12
    assert summary["hosts"]["codex"]["interpretability_cases"] == {"CASE_1": 3}
    assert summary["hosts"]["claude"]["interpretability_cases"] == {"CASE_1": 3}
    from agentic_conformance.experiment_scheduler import validate_terminal_marker

    marker = json.loads(result.marker_path.read_text(encoding="utf-8"))
    assert validate_terminal_marker(plan, marker) == marker


def test_neutral_worker_keeps_fixture_paths_out_of_deep_result_tree(tmp_path: Path) -> None:
    plan = _paired_plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    processes = {"codex": HostProcess("codex"), "claude": HostProcess("claude")}
    delegate = _factory(processes)
    observed_parents: list[Path] = []

    def capture(
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
        treatment: AuthTreatment,
    ) -> HostRuntime:
        observed_parents.append(workspace_parent)
        return delegate(binding, workspace_parent, before_execute, treatment)

    capture.executes_subprocess = False
    result = run_experiment(
        plan_path,
        plan.plan_digest,
        ancestry_reader=_neutral_ancestry,
        allow_nonlocal_executables_for_testing=True,
        runtime_factory=capture,
        source_state_reader=lambda _: (plan.benchmark_revision, ()),
        environment_reader=lambda: {"os": "nt", "python": "test"},
    )

    assert result.status == "COMPLETE"
    assert observed_parents == [Path(tempfile.gettempdir()).resolve()] * 4
    assert all(plan.output_root not in parent.parents for parent in observed_parents)
