from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from agentic_conformance.adapters.auth_fixture import auth_fixture_digest
from agentic_conformance.adapters.claude import ClaudeAdapter, ClaudeRunDescription
from agentic_conformance.adapters.codex import CodexAdapter, CodexRunDescription
from agentic_conformance.adapters.process import (
    ProcessResult,
    ProcessRunner,
    SubprocessRunner,
    utc_now,
)
from agentic_conformance.claude_trial import claude_config_digest
from agentic_conformance.codex_trial import codex_config_digest
from agentic_conformance.experiment_aggregate import (
    TrialOutcome,
    build_batch_summary,
    load_outcome,
)
from agentic_conformance.experiment_plan import (
    ExperimentPlan,
    HostBinding,
    build_auth_plan,
    load_plan,
    write_plan,
)
from agentic_conformance.experiment_worker import read_source_state
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import load_scenario

_TASK_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,199}")
_TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class ScheduledTaskSpec:
    task_name: str
    execution_identity: str
    python_executable: Path
    working_directory: Path
    plan_path: Path
    expected_plan_digest: str
    created_at: str
    arguments: str
    command_digest: str

    @classmethod
    def create(
        cls,
        *,
        task_name: str,
        execution_identity: str,
        python_executable: Path,
        working_directory: Path,
        plan_path: Path,
        expected_plan_digest: str,
        created_at: str,
    ) -> ScheduledTaskSpec:
        python = python_executable.resolve()
        working = working_directory.resolve()
        plan = plan_path.resolve()
        if not _TASK_NAME.fullmatch(task_name):
            raise ValueError("scheduled task name is unsafe")
        if not execution_identity or any(char in execution_identity for char in "\r\n\0"):
            raise ValueError("scheduled task execution identity is invalid")
        if not python.is_absolute() or not working.is_absolute() or not plan.is_absolute():
            raise ValueError("scheduled task paths must be absolute")
        if not plan.is_relative_to(working):
            raise ValueError("scheduled task plan must be contained by the working directory")
        if not _DIGEST.fullmatch(expected_plan_digest):
            raise ValueError("scheduled task plan digest is malformed")
        arguments = subprocess.list2cmdline(
            (
                "-m",
                "agentic_conformance.experiment_worker",
                "--plan",
                str(plan),
                "--expected-plan-digest",
                expected_plan_digest,
            )
        )
        action = {
            "command": str(python),
            "arguments": arguments,
            "working_directory": str(working),
            "execution_identity": execution_identity,
        }
        encoded = json.dumps(action, sort_keys=True, separators=(",", ":"))
        digest = "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()
        return cls(
            task_name,
            execution_identity,
            python,
            working,
            plan,
            expected_plan_digest,
            created_at,
            arguments,
            digest,
        )


def render_task_xml(spec: ScheduledTaskSpec) -> str:
    ET.register_namespace("", _TASK_NS)
    task = ET.Element(f"{{{_TASK_NS}}}Task", {"version": "1.4"})
    registration = ET.SubElement(task, f"{{{_TASK_NS}}}RegistrationInfo")
    ET.SubElement(registration, f"{{{_TASK_NS}}}Date").text = spec.created_at
    ET.SubElement(
        registration, f"{{{_TASK_NS}}}Description"
    ).text = "One-time Agentic Engineering Conformance M4 neutral worker"
    principals = ET.SubElement(task, f"{{{_TASK_NS}}}Principals")
    principal = ET.SubElement(principals, f"{{{_TASK_NS}}}Principal", {"id": "Author"})
    ET.SubElement(principal, f"{{{_TASK_NS}}}UserId").text = spec.execution_identity
    ET.SubElement(principal, f"{{{_TASK_NS}}}LogonType").text = "InteractiveToken"
    ET.SubElement(principal, f"{{{_TASK_NS}}}RunLevel").text = "LeastPrivilege"
    settings = ET.SubElement(task, f"{{{_TASK_NS}}}Settings")
    values = {
        "MultipleInstancesPolicy": "IgnoreNew",
        "DisallowStartIfOnBatteries": "false",
        "StopIfGoingOnBatteries": "false",
        "AllowHardTerminate": "true",
        "StartWhenAvailable": "false",
        "RunOnlyIfNetworkAvailable": "false",
        "AllowStartOnDemand": "true",
        "Enabled": "true",
        "Hidden": "false",
        "RunOnlyIfIdle": "false",
        "WakeToRun": "false",
        "ExecutionTimeLimit": "PT2H",
        "Priority": "7",
    }
    for name, value in values.items():
        ET.SubElement(settings, f"{{{_TASK_NS}}}{name}").text = value
    actions = ET.SubElement(task, f"{{{_TASK_NS}}}Actions", {"Context": "Author"})
    action = ET.SubElement(actions, f"{{{_TASK_NS}}}Exec")
    ET.SubElement(action, f"{{{_TASK_NS}}}Command").text = str(spec.python_executable)
    ET.SubElement(action, f"{{{_TASK_NS}}}Arguments").text = spec.arguments
    ET.SubElement(action, f"{{{_TASK_NS}}}WorkingDirectory").text = str(spec.working_directory)
    body = ET.tostring(task, encoding="unicode", short_empty_elements=False)
    return '<?xml version="1.0" encoding="UTF-16"?>\n' + body


class MarkerReader(Protocol):
    def __call__(self, path: Path) -> dict[str, object] | None: ...


class SchedulerController:
    def __init__(
        self,
        *,
        process_runner: ProcessRunner | None = None,
        executable: str = "schtasks.exe",
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        marker_reader: MarkerReader | None = None,
    ) -> None:
        self._process_runner = process_runner or SubprocessRunner()
        self._executable = executable
        self._clock = clock
        self._sleeper = sleeper
        self._marker_reader = marker_reader or _read_marker

    def register(self, spec: ScheduledTaskSpec) -> Path:
        collision = self._run((self._executable, "/Query", "/TN", spec.task_name))
        if collision.returncode == 0:
            raise RuntimeError(f"scheduled task already exists: {spec.task_name}")
        if collision.returncode != 1:
            raise RuntimeError("scheduled task collision probe failed")
        xml_path = spec.plan_path.parent / "scheduled-task.xml"
        temporary = xml_path.with_suffix(".xml.tmp")
        temporary.write_text(render_task_xml(spec), encoding="utf-16")
        temporary.replace(xml_path)
        created = self._run(
            (
                self._executable,
                "/Create",
                "/TN",
                spec.task_name,
                "/XML",
                str(xml_path),
            )
        )
        if created.returncode != 0:
            raise RuntimeError("scheduled task registration failed without elevation fallback")
        return xml_path

    def start(self, task_name: str) -> None:
        result = self._run((self._executable, "/Run", "/TN", task_name))
        if result.returncode != 0:
            raise RuntimeError("scheduled task start failed")

    def query(self, task_name: str) -> ProcessResult:
        result = self._run((self._executable, "/Query", "/TN", task_name, "/FO", "LIST", "/V"))
        if result.returncode != 0:
            raise RuntimeError("scheduled task query failed")
        return result

    def end(self, task_name: str) -> None:
        result = self._run((self._executable, "/End", "/TN", task_name))
        if result.returncode != 0:
            raise RuntimeError("scheduled task termination failed")

    def delete(self, task_name: str) -> None:
        result = self._run((self._executable, "/Delete", "/TN", task_name, "/F"))
        if result.returncode != 0:
            raise RuntimeError("scheduled task deletion failed")

    def wait(
        self,
        task_name: str,
        marker_path: Path,
        *,
        timeout_seconds: float,
        poll_seconds: float,
    ) -> dict[str, object]:
        if timeout_seconds <= 0 or poll_seconds <= 0:
            raise ValueError("scheduled batch timeout and poll interval must be positive")
        deadline = self._clock() + timeout_seconds
        while True:
            marker = self._marker_reader(marker_path)
            if marker is not None:
                return marker
            if self._clock() >= deadline:
                raise TimeoutError("scheduled batch exceeded its bounded timeout")
            self.query(task_name)
            self._sleeper(poll_seconds)

    def _run(self, command: tuple[str, ...]) -> ProcessResult:
        return self._process_runner.run(command, cwd=None, stdin=None, timeout_seconds=30.0)


def prepare_live_plan(
    source_root: Path, *, batch_id: str | None = None
) -> tuple[ExperimentPlan, Path]:
    source = source_root.resolve()
    head, status = read_source_state(source)
    if status:
        raise RuntimeError("source worktree must be clean before binding a live experiment plan")
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    if codex_path is None or claude_path is None:
        raise RuntimeError("both Codex and Claude executables are required before scheduling")
    codex = CodexAdapter(executable_resolver=lambda _: codex_path)
    claude = ClaudeAdapter(executable_resolver=lambda _: claude_path)
    if {"filesystem.read", "filesystem.write"} - codex.probe():
        raise RuntimeError("Codex subscription authentication is unavailable")
    if {"filesystem.read", "filesystem.write"} - claude.probe():
        raise RuntimeError("Claude subscription authentication is unavailable")
    if codex.probed_cli_version is None or claude.probed_cli_version is None:
        raise RuntimeError("host CLI version preflight was incomplete")
    if codex.probed_auth_mode != "chatgpt":
        raise RuntimeError("Codex preflight must use ChatGPT subscription authentication")
    if (
        claude.probed_auth_mode != "claude.ai"
        or claude.probed_auth_provider != "firstParty"
        or not claude.probed_subscription_type
    ):
        raise RuntimeError("Claude preflight must use first-party subscription authentication")

    scenario = load_scenario(
        source / "scenarios/authority/AUTH-001/scenario.json",
        source / "schemas/scenario.schema.json",
    )
    actual_batch = (
        batch_id
        or "m4-neutral-"
        + utc_now().replace("-", "").replace(":", "").replace("Z", "").split(".")[0].casefold()
    )
    output_root = source / "reports/runs" / actual_batch
    if output_root.exists():
        raise RuntimeError("experiment output root already exists")
    codex_description = CodexRunDescription(
        codex.probed_cli_version,
        (),
        source,
        "gpt-5.6-sol",
        "high",
        "default",
        "workspace-write",
        False,
        True,
        True,
    )
    claude_description = ClaudeRunDescription(
        claude.probed_cli_version,
        (),
        source,
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
    fixture_version = scenario.ground_truth.get("fixture_version")
    if not isinstance(fixture_version, str):
        raise RuntimeError("AUTH-001 fixture version is unavailable")
    plan = build_auth_plan(
        batch_id=actual_batch,
        benchmark_revision=head,
        source_root=source,
        output_root=output_root,
        scenario_version=scenario.version,
        scenario_digest=scenario_digest(scenario),
        fixture_version=fixture_version,
        fixture_digest=auth_fixture_digest(),
        codex=HostBinding(
            CodexAdapter.name,
            CodexAdapter.version,
            codex.probed_cli_version,
            str(Path(codex_path).resolve()),
            codex_description.model,
            codex_config_digest(codex_description),
            "workspace-write;network=false",
            "chatgpt",
            "openai",
            None,
        ),
        claude=HostBinding(
            ClaudeAdapter.name,
            ClaudeAdapter.version,
            claude.probed_cli_version,
            str(Path(claude_path).resolve()),
            claude_description.requested_model,
            claude_config_digest(claude_description),
            "safe-mode;no-shell;no-web",
            "claude.ai",
            "firstParty",
            claude.probed_subscription_type,
        ),
        created_at=utc_now(),
    )
    plan_path = output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    if read_source_state(source) != (head, ()):
        raise RuntimeError("source state changed while the experiment plan was bound")
    return plan, plan_path


def current_windows_identity() -> str:
    completed = subprocess.run(
        ("whoami.exe",),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=30.0,
    )
    identity = completed.stdout.strip()
    if completed.returncode != 0 or not identity:
        raise RuntimeError("current Windows identity could not be determined")
    return identity


def launch_plan(
    plan_path: Path,
    *,
    timeout_seconds: float = 3600.0,
    poll_seconds: float = 10.0,
    controller: SchedulerController | None = None,
    identity_reader: Callable[[], str] = current_windows_identity,
) -> dict[str, object]:
    plan = load_plan(plan_path)
    _assert_fresh_runtime_output(plan)
    identity = identity_reader()
    spec = ScheduledTaskSpec.create(
        task_name=f"AEC-M4-{plan.batch_id}",
        execution_identity=identity,
        python_executable=Path(sys.executable),
        working_directory=plan.source_root,
        plan_path=plan_path,
        expected_plan_digest=plan.plan_digest,
        created_at=utc_now(),
    )
    task_controller = controller or SchedulerController()
    record_path = plan.output_root / "scheduler-record.json"
    record: dict[str, object] = {
        "schema_version": "0.1",
        "task_name": spec.task_name,
        "creation_time": spec.created_at,
        "execution_identity": identity,
        "expected_plan_digest": spec.expected_plan_digest,
        "command_digest": spec.command_digest,
        "registered": False,
        "started": False,
        "termination_time": None,
        "termination_error": None,
        "deletion_time": None,
        "cleanup_error": None,
        "cleanup_deferred": None,
    }
    registered = False
    started = False
    try:
        xml_path = task_controller.register(spec)
        registered = True
        record["registered"] = True
        record["task_xml_digest"] = "sha256:" + hashlib.sha256(xml_path.read_bytes()).hexdigest()
        _atomic_json(record_path, record)
        task_controller.start(spec.task_name)
        started = True
        record["started"] = True
        _atomic_json(record_path, record)
        marker = task_controller.wait(
            spec.task_name,
            plan.output_root / "batch-complete.json",
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        validated = validate_terminal_marker(plan, marker)
        started = False
        record["worker_terminal_evidence_time"] = utc_now()
        record["terminal_status"] = validated.get("status")
        return validated
    except TimeoutError as error:
        if started:
            _terminate_started_task(task_controller, spec.task_name, record)
            started = False
        marker = _timeout_marker(plan, f"{type(error).__name__}: {error}")
        _atomic_json(plan.output_root / "batch-complete.json", marker)
        record["terminal_status"] = marker["status"]
        return validate_terminal_marker(plan, marker)
    except Exception:
        if started:
            _terminate_started_task(task_controller, spec.task_name, record)
            started = False
        raise
    finally:
        if registered and not started:
            try:
                task_controller.delete(spec.task_name)
                record["deletion_time"] = utc_now()
            except Exception as error:
                record["cleanup_error"] = f"{type(error).__name__}: {error}"
        elif registered:
            record["cleanup_deferred"] = (
                "scheduled task definition retained because its worker may still be active"
            )
        _atomic_json(record_path, record)


def _terminate_started_task(
    controller: SchedulerController,
    task_name: str,
    record: dict[str, object],
) -> None:
    try:
        controller.end(task_name)
    except Exception as error:
        record["termination_error"] = f"{type(error).__name__}: {error}"
        record["terminal_status"] = "BLOCKED_ACTIVE_TASK"
        raise RuntimeError(
            "scheduled worker termination failed; task definition retained"
        ) from error
    record["termination_time"] = utc_now()


def validate_terminal_marker(
    plan: ExperimentPlan,
    marker: Mapping[str, object],
) -> dict[str, object]:
    if marker.get("batch_id") != plan.batch_id or marker.get("plan_digest") != plan.plan_digest:
        raise ValueError("batch marker does not match the immutable experiment plan")
    status = marker.get("status")
    allowed = {
        "COMPLETE",
        "INVALID_NEUTRAL_ENVIRONMENT",
        "INVALID_SOURCE_STATE",
        "INVALID_BATCH",
        "BATCH_TIMEOUT",
    }
    if status not in allowed:
        raise ValueError("batch marker has an unsupported terminal status")
    outcomes = _load_batch_outcomes(plan)
    observed_digests = marker.get("outcome_digests")
    expected_digests = [outcome.outcome_digest for outcome in outcomes]
    if observed_digests != expected_digests:
        raise ValueError("batch marker outcome digests differ from persisted outcomes")
    if marker.get("recorded_trials") != len(outcomes):
        raise ValueError("batch marker recorded-trial count is inconsistent")
    if marker.get("result_digest") != _result_digest(expected_digests):
        raise ValueError("batch marker result digest is inconsistent")
    if status == "COMPLETE":
        if len(outcomes) != len(plan.trials):
            raise ValueError("complete marker does not contain all planned outcomes")
        summary_path = plan.output_root / "batch-summary.json"
        summary = _read_json_object(summary_path, "batch summary")
        summary_digest = _mapping_digest(summary, "summary_digest")
        if summary.get("summary_digest") != summary_digest:
            raise ValueError("batch summary digest is inconsistent")
        if marker.get("summary_digest") != summary_digest:
            raise ValueError("batch marker summary digest is inconsistent")
        if summary.get("plan_digest") != plan.plan_digest:
            raise ValueError("batch summary does not match the immutable experiment plan")
        expected_summary = build_batch_summary(plan, outcomes)
        if {
            key: value for key, value in summary.items() if key != "summary_digest"
        } != expected_summary:
            raise ValueError("batch summary differs from deterministic stored-evidence aggregate")
    elif marker.get("summary_digest") is not None:
        raise ValueError("non-complete batch marker cannot claim an aggregate summary")
    if status == "BATCH_TIMEOUT" and marker.get("missing_run_ids") != [
        trial.run_id for trial in plan.trials[len(outcomes) :]
    ]:
        raise ValueError("timeout marker missing-run list is inconsistent")
    return dict(marker)


def _load_batch_outcomes(plan: ExperimentPlan) -> tuple[TrialOutcome, ...]:
    state_path = plan.output_root / "batch-state.json"
    if not state_path.exists():
        return ()
    state = _read_json_object(state_path, "batch state")
    if state.get("plan_digest") != plan.plan_digest:
        raise ValueError("batch state does not match the immutable experiment plan")
    raw_outcomes = state.get("outcomes")
    if not isinstance(raw_outcomes, list):
        raise ValueError("batch state outcomes are malformed")
    outcomes = tuple(
        TrialOutcome.from_mapping(cast(dict[str, object], item))
        for item in raw_outcomes
        if isinstance(item, dict)
    )
    if len(outcomes) != len(raw_outcomes):
        raise ValueError("batch state outcome entry is malformed")
    expected = tuple(
        (trial.sequence, trial.run_id, trial.host, trial.ordinal)
        for trial in plan.trials[: len(outcomes)]
    )
    actual = tuple(
        (outcome.sequence, outcome.run_id, outcome.host, outcome.ordinal) for outcome in outcomes
    )
    if actual != expected:
        raise ValueError("batch state outcomes are not a valid plan prefix")
    for outcome in outcomes:
        persisted = load_outcome(plan.output_root / "outcomes" / f"{outcome.run_id}.json")
        if persisted != outcome:
            raise ValueError("uniform trial outcome differs from batch state")
    return outcomes


def _result_digest(outcome_digests: list[str]) -> str:
    encoded = json.dumps(outcome_digests, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _mapping_digest(value: Mapping[str, object], digest_key: str) -> str:
    payload = {key: item for key, item in value.items() if key != digest_key}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is unreadable") from error
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    return cast(dict[str, object], raw)


def _timeout_marker(plan: ExperimentPlan, limitation: str) -> dict[str, object]:
    try:
        outcomes = _load_batch_outcomes(plan)
    except ValueError as error:
        outcomes = ()
        limitation = f"{limitation}; persisted partial state invalid: {error}"
    digests = [outcome.outcome_digest for outcome in outcomes]
    return {
        "schema_version": "0.1",
        "batch_id": plan.batch_id,
        "status": "BATCH_TIMEOUT",
        "plan_digest": plan.plan_digest,
        "summary_digest": None,
        "outcome_digests": digests,
        "result_digest": _result_digest(digests),
        "recorded_trials": len(outcomes),
        "missing_run_ids": [trial.run_id for trial in plan.trials[len(outcomes) :]],
        "limitation": limitation,
    }


def _assert_fresh_runtime_output(plan: ExperimentPlan) -> None:
    allowed = {"experiment-plan.json"}
    existing = sorted(path.name for path in plan.output_root.iterdir() if path.name not in allowed)
    if existing:
        raise RuntimeError(
            "experiment output root contains pre-existing runtime artifacts: " + ", ".join(existing)
        )


def _read_marker(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("batch marker must be an object")
    return cast(dict[str, object], raw)


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or launch an M4 neutral scheduled batch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--source-root", type=Path, default=Path.cwd())
    prepare.add_argument("--batch-id")
    launch = subparsers.add_parser("launch")
    launch.add_argument("--plan", type=Path, required=True)
    launch.add_argument("--timeout-seconds", type=float, default=3600.0)
    launch.add_argument("--poll-seconds", type=float, default=10.0)
    parsed = parser.parse_args(arguments)
    if parsed.command == "prepare":
        plan, path = prepare_live_plan(parsed.source_root, batch_id=parsed.batch_id)
        print(json.dumps({"plan": str(path), "plan_digest": plan.plan_digest}, sort_keys=True))
        return 0
    marker = launch_plan(
        parsed.plan, timeout_seconds=parsed.timeout_seconds, poll_seconds=parsed.poll_seconds
    )
    print(json.dumps(marker, sort_keys=True))
    return 0 if marker.get("status") == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
