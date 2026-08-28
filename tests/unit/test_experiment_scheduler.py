from __future__ import annotations

from pathlib import Path

import pytest

from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.experiment_plan import HostBinding, build_auth_plan, write_plan
from agentic_conformance.experiment_scheduler import (
    ScheduledTaskSpec,
    SchedulerController,
    render_task_xml,
)


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
