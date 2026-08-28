from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from agentic_conformance.adapters.auth_fixture import auth_fixture_digest
from agentic_conformance.adapters.base import Adapter
from agentic_conformance.adapters.claude import ClaudeAdapter, ClaudeRunDescription
from agentic_conformance.adapters.codex import CodexAdapter, CodexRunDescription
from agentic_conformance.claude_trial import (
    claude_config_digest,
)
from agentic_conformance.claude_trial import (
    run_auth_trial as run_claude_auth_trial,
)
from agentic_conformance.codex_trial import (
    codex_config_digest,
)
from agentic_conformance.codex_trial import (
    run_auth_trial as run_codex_auth_trial,
)
from agentic_conformance.experiment_aggregate import (
    TrialOutcome,
    build_batch_summary,
    file_digest,
    load_outcome,
    write_outcome,
    write_summary,
)
from agentic_conformance.experiment_plan import (
    ExperimentPlan,
    HostBinding,
    TrialSpec,
    load_plan,
)
from agentic_conformance.observed_process import ObservedProcessRunner
from agentic_conformance.process_ancestry import (
    ProcessAncestry,
    assess_worker_neutrality,
    capture_windows_ancestry,
    sanitized_environment,
)
from agentic_conformance.result import Outcome, RunClassification, RunResult
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import load_scenario


class RuntimeFactory(Protocol):
    def __call__(
        self,
        binding: HostBinding,
        workspace_parent: Path,
        before_execute: Callable[[object], None],
    ) -> HostRuntime: ...


@dataclass(frozen=True, slots=True)
class HostRuntime:
    adapter: Adapter
    observations: Callable[[], tuple[Mapping[str, object], ...]]


class PersistedArtifacts(Protocol):
    @property
    def evidence_path(self) -> Path: ...
    @property
    def manifest_path(self) -> Path: ...
    @property
    def result(self) -> RunResult: ...
    @property
    def rescored(self) -> RunResult: ...


@dataclass(frozen=True, slots=True)
class WorkerResult:
    status: str
    exit_code: int
    outcomes: tuple[TrialOutcome, ...]
    summary_path: Path
    marker_path: Path


SourceStateReader = Callable[[Path], tuple[str, tuple[str, ...]]]


def run_experiment(
    plan_path: Path,
    expected_plan_digest: str,
    *,
    ancestry_reader: Callable[[int], ProcessAncestry] = capture_windows_ancestry,
    runtime_factory: RuntimeFactory | None = None,
    source_state_reader: SourceStateReader | None = None,
    environment_reader: Callable[[], Mapping[str, str]] = sanitized_environment,
) -> WorkerResult:
    plan = load_plan(plan_path)
    if plan.plan_digest != expected_plan_digest:
        raise ValueError("experiment plan differs from scheduled digest binding")
    summary_path = plan.output_root / "batch-summary.json"
    marker_path = plan.output_root / "batch-complete.json"
    state_reader = source_state_reader or read_source_state
    _verify_plan_bindings(plan, state_reader)

    ancestry = ancestry_reader(os.getpid())
    neutrality = assess_worker_neutrality(ancestry)
    envelope = {
        "schema_version": "0.1",
        "plan_digest": plan.plan_digest,
        "execution_identity": getpass.getuser(),
        "environment": dict(environment_reader()),
        "worker_ancestry": ancestry.to_mapping(),
        "neutrality": {
            "valid": neutrality.valid,
            "status": neutrality.status,
            "reason": neutrality.reason,
        },
    }
    _atomic_json(plan.output_root / "worker-envelope.json", envelope)
    if not neutrality.valid:
        marker = _terminal_marker(plan, neutrality.status, (), None)
        _atomic_json(marker_path, marker)
        return WorkerResult(neutrality.status, 20, (), summary_path, marker_path)

    factory = runtime_factory or default_runtime_factory
    workspace_parent = Path(tempfile.gettempdir()).resolve()
    runtimes: dict[str, HostRuntime] = {}
    availability: dict[str, tuple[RunClassification, str] | None] = {}
    for binding in plan.hosts:
        callback = _execution_preflight(plan, binding, state_reader)
        try:
            runtime = factory(binding, workspace_parent, callback)
            _validate_runtime_identity(binding, runtime.adapter)
            capabilities = runtime.adapter.probe()
            missing = {"filesystem.read", "filesystem.write"} - capabilities
            observed_version = getattr(runtime.adapter, "probed_cli_version", None)
            if observed_version != binding.cli_version:
                raise RuntimeError("host CLI version differs from immutable plan binding")
            if not missing:
                _validate_auth_binding(binding, runtime.adapter)
            runtimes[binding.name] = runtime
            availability[binding.name] = (
                (
                    RunClassification.UNSUPPORTED,
                    f"worker-context host capability unavailable: {', '.join(sorted(missing))}",
                )
                if missing
                else None
            )
        except Exception as error:
            availability[binding.name] = (RunClassification.INVALID_RUN, _safe_error(error))

    outcomes: list[TrialOutcome] = []
    try:
        for trial in plan.trials:
            _verify_source(plan, state_reader)
            binding = _binding(plan, trial.host)
            unavailable = availability[binding.name]
            if unavailable is not None:
                classification, reason = unavailable
                outcome = _not_run_outcome(trial, binding, classification, reason)
                _persist_non_evidence_outcome(plan.output_root / "runs", outcome)
            else:
                runtime = runtimes[binding.name]
                outcome = _run_bound_trial(plan, trial, binding, runtime)
            write_outcome(
                plan.output_root / "outcomes" / f"{outcome.run_id}.json",
                outcome,
            )
            outcomes.append(outcome)
            _write_batch_state(plan, tuple(outcomes))
            _verify_source(plan, state_reader)
    except Exception as error:
        status = "INVALID_SOURCE_STATE" if "source" in str(error).casefold() else "INVALID_BATCH"
        marker = _terminal_marker(plan, status, tuple(outcomes), None, _safe_error(error))
        _atomic_json(marker_path, marker)
        return WorkerResult(status, 21, tuple(outcomes), summary_path, marker_path)

    persisted_outcomes = tuple(
        load_outcome(plan.output_root / "outcomes" / f"{trial.run_id}.json")
        for trial in plan.trials
    )
    summary = build_batch_summary(plan, persisted_outcomes)
    summary_digest = write_summary(summary_path, summary)
    marker = _terminal_marker(plan, "COMPLETE", persisted_outcomes, summary_digest)
    _atomic_json(marker_path, marker)
    return WorkerResult("COMPLETE", 0, persisted_outcomes, summary_path, marker_path)


def _run_bound_trial(
    plan: ExperimentPlan,
    trial: TrialSpec,
    binding: HostBinding,
    runtime: HostRuntime,
) -> TrialOutcome:
    observation_start = len(runtime.observations())

    def diagnostics() -> Mapping[str, str]:
        observed = runtime.observations()[observation_start:]
        return {
            "process-ancestry.json": json.dumps(
                {"schema_version": "0.1", "processes": [dict(item) for item in observed]},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        }

    artifacts: PersistedArtifacts
    try:
        if trial.host == "codex":
            if not isinstance(runtime.adapter, CodexAdapter):
                raise TypeError("Codex plan slot requires CodexAdapter")
            artifacts = run_codex_auth_trial(
                plan.output_root / "runs",
                runtime.adapter,
                run_id=trial.run_id,
                additional_diagnostics=diagnostics,
            )
            codex_observation = runtime.adapter.last_observation
            if codex_observation is None:
                raise RuntimeError("Codex observation is unavailable")
            process_returncode = codex_observation.process.returncode
        elif trial.host == "claude":
            if not isinstance(runtime.adapter, ClaudeAdapter):
                raise TypeError("Claude plan slot requires ClaudeAdapter")
            artifacts = run_claude_auth_trial(
                plan.output_root / "runs",
                runtime.adapter,
                run_id=trial.run_id,
                additional_diagnostics=diagnostics,
            )
            claude_observation = runtime.adapter.last_observation
            if claude_observation is None:
                raise RuntimeError("Claude observation is unavailable")
            process_returncode = claude_observation.process.returncode
        else:
            raise ValueError("unsupported experiment host")
    except Exception as error:
        diagnostic_artifacts = diagnostics()
        attempted = len(runtime.observations()) > observation_start
        outcome = TrialOutcome.create(
            sequence=trial.sequence,
            run_id=trial.run_id,
            host=trial.host,
            ordinal=trial.ordinal,
            attempted=attempted,
            classification=RunClassification.INVALID_RUN,
            functional=Outcome.NOT_RUN,
            control=Outcome.NOT_RUN,
            limitations=(
                _safe_error(error),
                "requested model was not observed because the trial did not complete",
            ),
            cli_version=binding.cli_version,
            requested_model=binding.requested_model,
            observed_model_identifier=None,
            config_digest=binding.config_digest,
            evidence_digest=None,
            manifest_digest=None,
            rescored_equal=None,
            process_returncode=None,
        )
        _persist_non_evidence_outcome(
            plan.output_root / "runs",
            outcome,
            additional_diagnostics=diagnostic_artifacts,
        )
        return outcome

    manifest_raw: Any = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest_raw, dict):
        raise RuntimeError("persisted run manifest is malformed")
    manifest = cast(dict[str, Any], manifest_raw)
    result = artifacts.result
    limitations = manifest.get("limitations")
    safe_limitations = (
        tuple(item for item in limitations if isinstance(item, str))
        if isinstance(limitations, list)
        else ("persisted run limitations were malformed",)
    )
    if trial.host == "codex":
        safe_limitations += (
            "Codex model was requested/configured but not independently observed in this run.",
        )
    return TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=True,
        classification=result.classification,
        functional=result.functional,
        control=result.control,
        limitations=safe_limitations,
        cli_version=binding.cli_version,
        requested_model=binding.requested_model,
        observed_model_identifier=(
            cast(str | None, manifest.get("model_identifier")) if trial.host == "claude" else None
        ),
        config_digest=binding.config_digest,
        evidence_digest=file_digest(artifacts.evidence_path),
        manifest_digest=file_digest(artifacts.manifest_path),
        rescored_equal=artifacts.result == artifacts.rescored,
        process_returncode=process_returncode,
    )


def _not_run_outcome(
    trial: TrialSpec,
    binding: HostBinding,
    classification: RunClassification,
    reason: str,
) -> TrialOutcome:
    return TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=False,
        classification=classification,
        functional=Outcome.NOT_RUN,
        control=Outcome.NOT_RUN,
        limitations=(
            reason,
            "requested model was not observed because the trial did not execute",
        ),
        cli_version=binding.cli_version,
        requested_model=binding.requested_model,
        observed_model_identifier=None,
        config_digest=binding.config_digest,
        evidence_digest=None,
        manifest_digest=None,
        rescored_equal=None,
        process_returncode=None,
    )


def default_runtime_factory(
    binding: HostBinding,
    workspace_parent: Path,
    before_execute: Callable[[object], None],
) -> HostRuntime:
    runner = ObservedProcessRunner(observe_command=_is_live_host_command)

    def resolver(_: str) -> str:
        return binding.executable

    if binding.name == "codex":
        adapter: Adapter = CodexAdapter(
            process_runner=runner,
            executable_resolver=resolver,
            workspace_parent=workspace_parent,
            model=binding.requested_model,
            before_execute=before_execute,
        )
    elif binding.name == "claude":
        adapter = ClaudeAdapter(
            process_runner=runner,
            executable_resolver=resolver,
            workspace_parent=workspace_parent,
            model=binding.requested_model,
            before_execute=before_execute,
        )
    else:
        raise ValueError("unsupported host binding")
    return HostRuntime(
        adapter=adapter,
        observations=lambda: tuple(
            cast(Mapping[str, object], observation.to_mapping())
            for observation in runner.observations
        ),
    )


def _is_live_host_command(command: tuple[str, ...]) -> bool:
    return not (
        command[-1:] == ("--version",)
        or command[-2:] == ("login", "status")
        or command[-3:] == ("auth", "status", "--json")
    )


def read_source_state(source_root: Path) -> tuple[str, tuple[str, ...]]:
    head = _git(source_root, "rev-parse", "HEAD").strip()
    status = tuple(
        line
        for line in _git(
            source_root, "status", "--porcelain=v1", "--untracked-files=all"
        ).splitlines()
        if line
    )
    return head, status


def _verify_plan_bindings(plan: ExperimentPlan, state_reader: SourceStateReader) -> None:
    _verify_source(plan, state_reader)
    scenario = load_scenario(
        plan.source_root / "scenarios/authority/AUTH-001/scenario.json",
        plan.source_root / "schemas/scenario.schema.json",
    )
    if (
        scenario.scenario_id != plan.scenario_id
        or scenario.version != plan.scenario_version
        or scenario_digest(scenario) != plan.scenario_digest
    ):
        raise ValueError("experiment plan scenario binding differs from source")
    fixture_version = scenario.ground_truth.get("fixture_version")
    if fixture_version != plan.fixture_version or auth_fixture_digest() != plan.fixture_digest:
        raise ValueError("experiment plan fixture binding differs from source")


def _verify_source(plan: ExperimentPlan, state_reader: SourceStateReader) -> None:
    head, status = state_reader(plan.source_root)
    if head != plan.benchmark_revision:
        raise RuntimeError("benchmark source revision differs from immutable plan")
    if status:
        raise RuntimeError("benchmark source worktree is dirty during neutral measurement")


def _execution_preflight(
    plan: ExperimentPlan, binding: HostBinding, state_reader: SourceStateReader
) -> Callable[[object], None]:
    def verify(description: object) -> None:
        _verify_source(plan, state_reader)
        _validate_description(binding, description)

    return verify


def _validate_description(binding: HostBinding, description: object) -> None:
    if binding.name == "codex":
        if not isinstance(description, CodexRunDescription):
            raise TypeError("Codex runtime produced the wrong description type")
        if (
            description.cli_version != binding.cli_version
            or description.model != binding.requested_model
            or codex_config_digest(description) != binding.config_digest
            or description.sandbox != "workspace-write"
            or description.shell_network
        ):
            raise RuntimeError("Codex invocation differs from immutable plan binding")
    elif binding.name == "claude":
        if not isinstance(description, ClaudeRunDescription):
            raise TypeError("Claude runtime produced the wrong description type")
        if (
            description.cli_version != binding.cli_version
            or description.requested_model != binding.requested_model
            or claude_config_digest(description) != binding.config_digest
            or not description.safe_mode
            or description.target_shell_available
            or description.target_web_available
        ):
            raise RuntimeError("Claude invocation differs from immutable plan binding")
    else:
        raise ValueError("unsupported host binding")


def _validate_runtime_identity(binding: HostBinding, adapter: Adapter) -> None:
    if adapter.name != binding.name or adapter.version != binding.adapter_version:
        raise RuntimeError("adapter identity differs from immutable plan binding")


def _validate_auth_binding(binding: HostBinding, adapter: Adapter) -> None:
    observed_mode = getattr(adapter, "probed_auth_mode", None)
    if observed_mode != binding.auth_mode:
        raise RuntimeError("host authentication mode differs from immutable plan binding")
    observed_provider: str | None
    observed_subscription: str | None
    if binding.name == "codex":
        observed_provider = "openai"
        observed_subscription = None
    else:
        observed_provider = cast(str | None, getattr(adapter, "probed_auth_provider", None))
        observed_subscription = cast(str | None, getattr(adapter, "probed_subscription_type", None))
    if observed_provider != binding.auth_provider:
        raise RuntimeError("host authentication provider differs from immutable plan binding")
    if observed_subscription != binding.subscription_type:
        raise RuntimeError("host subscription type differs from immutable plan binding")


def _binding(plan: ExperimentPlan, host: str) -> HostBinding:
    for binding in plan.hosts:
        if binding.name == host:
            return binding
    raise ValueError("trial host has no plan binding")


def _persist_non_evidence_outcome(
    output_root: Path,
    outcome: TrialOutcome,
    *,
    additional_diagnostics: Mapping[str, str] | None = None,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / outcome.run_id
    if target.exists():
        raise FileExistsError(f"trial output already exists: {outcome.run_id}")
    staging = output_root / f".{outcome.run_id}.staging-{uuid.uuid4().hex[:8]}"
    staging.mkdir()
    try:
        _atomic_json(staging / "outcome.json", outcome.to_mapping())
        for relative_name, content in (additional_diagnostics or {}).items():
            if Path(relative_name).name != relative_name:
                raise ValueError("diagnostic artifact name must be a single safe path component")
            (staging / relative_name).write_text(content, encoding="utf-8")
        staging.replace(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _write_batch_state(plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]) -> None:
    _atomic_json(
        plan.output_root / "batch-state.json",
        {
            "schema_version": "0.1",
            "plan_digest": plan.plan_digest,
            "outcomes": [outcome.to_mapping() for outcome in outcomes],
        },
    )


def _terminal_marker(
    plan: ExperimentPlan,
    status: str,
    outcomes: tuple[TrialOutcome, ...],
    summary_digest: str | None,
    limitation: str | None = None,
) -> dict[str, object]:
    outcome_digests = [outcome.outcome_digest for outcome in outcomes]
    result_digest = (
        "sha256:"
        + hashlib.sha256(json.dumps(outcome_digests, separators=(",", ":")).encode()).hexdigest()
    )
    return {
        "schema_version": "0.1",
        "batch_id": plan.batch_id,
        "status": status,
        "plan_digest": plan.plan_digest,
        "summary_digest": summary_digest,
        "outcome_digests": outcome_digests,
        "result_digest": result_digest,
        "recorded_trials": len(outcomes),
        "limitation": limitation,
    }


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _git(source_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(source_root), *arguments),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=30.0,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Git source-state query failed: {arguments[0]}")
    return completed.stdout


def _safe_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bound neutral AEC experiment plan")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--expected-plan-digest", required=True)
    parsed = parser.parse_args(arguments)
    try:
        result = run_experiment(parsed.plan, parsed.expected_plan_digest)
    except Exception as error:
        print(json.dumps({"status": "INVALID_PLAN", "error": _safe_error(error)}))
        return 30
    print(
        json.dumps(
            {
                "status": result.status,
                "recorded_trials": len(result.outcomes),
                "marker": str(result.marker_path),
            },
            sort_keys=True,
        )
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
