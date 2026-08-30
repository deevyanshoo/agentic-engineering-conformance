from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.experiment_aggregate import (
    TrialOutcome,
    build_batch_summary,
    write_outcome,
    write_summary,
)
from agentic_conformance.experiment_plan import HostBinding, build_auth_plan, write_plan
from agentic_conformance.experiment_scheduler import (
    ScheduledTaskSpec,
    SchedulerController,
    _timeout_marker,
    launch_plan,
    render_task_xml,
    validate_terminal_marker,
)
from agentic_conformance.result import Outcome, RunClassification


class QueueRunner:
    def __init__(self, results: list[ProcessResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del cwd, stdin, timeout_seconds
        self.calls.append(command)
        return self.results.pop(0)


def _result(code: int = 0, stdout: str = "", stderr: str = "") -> ProcessResult:
    return ProcessResult(code, stdout, stderr, "2026-08-28T12:00:00Z", "2026-08-28T12:00:01Z")


def _plan(tmp_path: Path):
    def host(name: str) -> HostBinding:
        return HostBinding(
            name,
            "1.0.0",
            "2.0.0",
            f"C:/tools/{name}.CMD",
            f"{name}-model",
            "sha256:" + "c" * 64,
            f"{name}-sandbox",
            "chatgpt" if name == "codex" else "claude.ai",
            "openai" if name == "codex" else "firstParty",
            None if name == "codex" else "pro",
        )

    return build_auth_plan(
        batch_id="m4-neutral-scheduler",
        benchmark_revision="a" * 40,
        source_root=tmp_path.resolve(),
        output_root=(tmp_path / "reports/runs/m4-neutral-scheduler").resolve(),
        scenario_version="1.0.0",
        scenario_digest="sha256:" + "b" * 64,
        fixture_version="1.0.0",
        fixture_digest="sha256:" + "d" * 64,
        codex=host("codex"),
        claude=host("claude"),
        created_at="2026-08-28T12:00:00Z",
    )


def _spec(tmp_path: Path) -> ScheduledTaskSpec:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    return ScheduledTaskSpec.create(
        task_name="AEC-M4-m4-neutral-scheduler",
        execution_identity="DESKTOP\\founder",
        python_executable=Path("C:/Python/python.exe"),
        working_directory=plan.source_root,
        plan_path=plan_path,
        expected_plan_digest=plan.plan_digest,
        created_at="2026-08-28T12:01:00Z",
    )


def test_task_xml_is_current_user_least_privilege_and_literal(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    xml = render_task_xml(spec)

    assert "InteractiveToken" in xml
    assert "LeastPrivilege" in xml
    assert "DESKTOP\\founder" in xml
    assert str(spec.python_executable) in xml
    assert "agentic_conformance.experiment_worker" in xml
    assert str(spec.plan_path) in xml
    assert str(spec.working_directory) in xml
    assert "Password" not in xml
    assert "HighestAvailable" not in xml
    assert "Start-Process" not in xml
    assert "<Triggers>" not in xml
    assert spec.command_digest.startswith("sha256:")


def test_controller_registers_runs_queries_and_deletes_exact_task(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    process = QueueRunner([_result(1), _result(), _result(), _result(), _result()])
    controller = SchedulerController(process_runner=process, executable="schtasks.exe")

    xml_path = controller.register(spec)
    controller.start(spec.task_name)
    controller.query(spec.task_name)
    controller.delete(spec.task_name)

    assert xml_path == spec.plan_path.parent / "scheduled-task.xml"
    assert process.calls == [
        ("schtasks.exe", "/Query", "/TN", spec.task_name),
        ("schtasks.exe", "/Create", "/TN", spec.task_name, "/XML", str(xml_path)),
        ("schtasks.exe", "/Run", "/TN", spec.task_name),
        ("schtasks.exe", "/Query", "/TN", spec.task_name, "/FO", "LIST", "/V"),
        ("schtasks.exe", "/Delete", "/TN", spec.task_name, "/F"),
    ]
    assert not any("/RP" in call or "/RL" in call for call in process.calls)


def test_controller_refuses_collision_and_never_overwrites(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    process = QueueRunner([_result(0)])
    controller = SchedulerController(process_runner=process, executable="schtasks.exe")
    with pytest.raises(RuntimeError, match="already exists"):
        controller.register(spec)
    assert len(process.calls) == 1


def test_bounded_monitor_observes_marker_without_mutating_worker(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    process = QueueRunner([_result(), _result()])
    times = iter((0.0, 1.0, 2.0))
    sleeps: list[float] = []
    polls = 0

    def marker_reader(path: Path) -> dict[str, object] | None:
        nonlocal polls
        polls += 1
        if polls == 2:
            return {"status": "COMPLETE", "plan_digest": _plan(tmp_path).plan_digest}
        return None

    controller = SchedulerController(
        process_runner=process,
        executable="schtasks.exe",
        clock=lambda: next(times),
        sleeper=sleeps.append,
        marker_reader=marker_reader,
    )
    marker = controller.wait(
        spec.task_name,
        spec.plan_path.parent / "batch-complete.json",
        timeout_seconds=10.0,
        poll_seconds=1.0,
    )

    assert marker["status"] == "COMPLETE"
    assert sleeps == [1.0]
    assert process.calls == [
        ("schtasks.exe", "/Query", "/TN", spec.task_name, "/FO", "LIST", "/V"),
    ]


def test_monitor_timeout_is_bounded(tmp_path: Path) -> None:
    process = QueueRunner([_result(), _result()])
    times = iter((0.0, 1.0, 2.0, 3.0))
    controller = SchedulerController(
        process_runner=process,
        executable="schtasks.exe",
        clock=lambda: next(times),
        sleeper=lambda _: None,
        marker_reader=lambda _: None,
    )
    with pytest.raises(TimeoutError, match="scheduled batch"):
        controller.wait(
            "AEC-M4-timeout",
            tmp_path / "missing.json",
            timeout_seconds=2.0,
            poll_seconds=1.0,
        )


def test_terminal_marker_rejects_stale_or_unbound_identity(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    marker = {
        "batch_id": "stale-batch",
        "plan_digest": plan.plan_digest,
        "status": "COMPLETE",
    }
    with pytest.raises(ValueError, match="immutable experiment plan"):
        validate_terminal_marker(plan, marker)


def test_timeout_marker_preserves_digest_bound_partial_outcome(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    trial = plan.trials[0]
    outcome = TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=False,
        classification=RunClassification.UNSUPPORTED,
        functional=Outcome.NOT_RUN,
        control=Outcome.NOT_RUN,
        limitations=("host unavailable",),
        cli_version=plan.hosts[0].cli_version,
        requested_model=plan.hosts[0].requested_model,
        observed_model_identifier=None,
        config_digest=plan.hosts[0].config_digest,
        evidence_digest=None,
        manifest_digest=None,
        rescored_equal=None,
        process_returncode=None,
    )
    write_outcome(plan.output_root / "outcomes" / f"{trial.run_id}.json", outcome)
    state = {
        "schema_version": "0.1",
        "plan_digest": plan.plan_digest,
        "outcomes": [outcome.to_mapping()],
    }
    state_path = plan.output_root / "batch-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")

    marker = _timeout_marker(plan, "bounded timeout")

    assert marker["status"] == "BATCH_TIMEOUT"
    assert marker["recorded_trials"] == 1
    assert marker["outcome_digests"] == [outcome.outcome_digest]
    assert marker["missing_run_ids"] == [trial.run_id for trial in plan.trials[1:]]
    assert validate_terminal_marker(plan, marker) == marker


class TerminationFailureController:
    def __init__(self) -> None:
        self.deleted = False

    def register(self, spec: ScheduledTaskSpec) -> Path:
        path = spec.plan_path.parent / "scheduled-task.xml"
        path.write_text("<Task />", encoding="utf-8")
        return path

    def start(self, task_name: str) -> None:
        del task_name

    def wait(
        self,
        task_name: str,
        marker_path: Path,
        *,
        timeout_seconds: float,
        poll_seconds: float,
    ) -> dict[str, object]:
        del task_name, marker_path, timeout_seconds, poll_seconds
        raise TimeoutError("synthetic bounded timeout")

    def end(self, task_name: str) -> None:
        del task_name
        raise RuntimeError("synthetic termination failure")

    def delete(self, task_name: str) -> None:
        del task_name
        self.deleted = True


def test_launch_retains_task_and_records_blocker_when_termination_fails(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    controller = TerminationFailureController()

    with pytest.raises(RuntimeError, match="task definition retained"):
        launch_plan(
            plan_path,
            timeout_seconds=1.0,
            poll_seconds=0.1,
            controller=controller,  # type: ignore[arg-type]
            identity_reader=lambda: "DESKTOP\\founder",
        )

    assert controller.deleted is False
    assert not (plan.output_root / "batch-complete.json").exists()
    record = json.loads((plan.output_root / "scheduler-record.json").read_text(encoding="utf-8"))
    assert record["terminal_status"] == "BLOCKED_ACTIVE_TASK"
    assert "termination failure" in record["termination_error"]
    assert "may still be active" in record["cleanup_deferred"]


class ValidTerminalController:
    def __init__(self, plan) -> None:
        self.plan = plan
        self.deleted = False

    def register(self, spec: ScheduledTaskSpec) -> Path:
        path = spec.plan_path.parent / "scheduled-task.xml"
        path.write_text("<Task />", encoding="utf-8")
        return path

    def start(self, task_name: str) -> None:
        del task_name

    def wait(
        self,
        task_name: str,
        marker_path: Path,
        *,
        timeout_seconds: float,
        poll_seconds: float,
    ) -> dict[str, object]:
        del task_name, timeout_seconds, poll_seconds
        outcomes = []
        for trial in self.plan.trials:
            binding = next(item for item in self.plan.hosts if item.name == trial.host)
            outcome = TrialOutcome.create(
                sequence=trial.sequence,
                run_id=trial.run_id,
                host=trial.host,
                ordinal=trial.ordinal,
                attempted=False,
                classification=RunClassification.UNSUPPORTED,
                functional=Outcome.NOT_RUN,
                control=Outcome.NOT_RUN,
                limitations=("host unavailable",),
                cli_version=binding.cli_version,
                requested_model=binding.requested_model,
                observed_model_identifier=None,
                config_digest=binding.config_digest,
                evidence_digest=None,
                manifest_digest=None,
                rescored_equal=None,
                process_returncode=None,
            )
            outcomes.append(outcome)
            write_outcome(
                self.plan.output_root / "outcomes" / f"{trial.run_id}.json",
                outcome,
            )
        state = {
            "schema_version": "0.1",
            "plan_digest": self.plan.plan_digest,
            "outcomes": [outcome.to_mapping() for outcome in outcomes],
        }
        (self.plan.output_root / "batch-state.json").write_text(
            json.dumps(state),
            encoding="utf-8",
        )
        summary_digest = write_summary(
            self.plan.output_root / "batch-summary.json",
            build_batch_summary(self.plan, tuple(outcomes)),
        )
        digests = [outcome.outcome_digest for outcome in outcomes]
        result_digest = (
            "sha256:"
            + hashlib.sha256(json.dumps(digests, separators=(",", ":")).encode()).hexdigest()
        )
        marker = {
            "schema_version": "0.1",
            "batch_id": self.plan.batch_id,
            "status": "COMPLETE",
            "plan_digest": self.plan.plan_digest,
            "summary_digest": summary_digest,
            "outcome_digests": digests,
            "result_digest": result_digest,
            "recorded_trials": 6,
            "limitation": None,
        }
        marker_path.write_text(json.dumps(marker), encoding="utf-8")
        return marker

    def end(self, task_name: str) -> None:
        raise AssertionError(f"terminal task must not be ended: {task_name}")

    def delete(self, task_name: str) -> None:
        del task_name
        self.deleted = True


def test_launch_deletes_exact_task_after_valid_terminal_marker(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    controller = ValidTerminalController(plan)

    marker = launch_plan(
        plan_path,
        controller=controller,  # type: ignore[arg-type]
        identity_reader=lambda: "DESKTOP\\founder",
    )

    assert marker["status"] == "COMPLETE"
    assert controller.deleted is True
    record = json.loads((plan.output_root / "scheduler-record.json").read_text(encoding="utf-8"))
    assert record["deletion_time"] is not None
    assert record["cleanup_deferred"] is None
    assert record["worker_terminal_evidence_time"] is not None


class DeletionFailureController(ValidTerminalController):
    def delete(self, task_name: str) -> None:
        del task_name
        raise RuntimeError("scheduler deletion failure")


def test_launch_blocks_when_terminal_task_deletion_fails(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan_path = plan.output_root / "experiment-plan.json"
    write_plan(plan_path, plan)
    controller = DeletionFailureController(plan)

    with pytest.raises(RuntimeError, match="scheduled task deletion failed"):
        launch_plan(
            plan_path,
            controller=controller,  # type: ignore[arg-type]
            identity_reader=lambda: "DESKTOP\\founder",
        )

    record = json.loads((plan.output_root / "scheduler-record.json").read_text(encoding="utf-8"))
    assert record["deletion_time"] is None
    assert "scheduler deletion failure" in record["cleanup_error"]
    assert record["terminal_status"] == "COMPLETE"
