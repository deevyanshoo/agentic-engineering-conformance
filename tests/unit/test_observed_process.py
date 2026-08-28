from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agentic_conformance.observed_process import ObservedProcessRunner
from agentic_conformance.process_ancestry import ProcessAncestry, ProcessNode


def _ancestry(pid: int) -> ProcessAncestry:
    return ProcessAncestry(
        subject_pid=pid,
        nodes=(ProcessNode(pid, 1, "python.exe", sys.executable),),
        captured_at="2026-08-28T12:00:00Z",
        complete=False,
        cycle_detected=False,
    )


def test_runs_without_shell_and_passively_records_child_pid(tmp_path: Path) -> None:
    observed: list[int] = []

    def read_ancestry(pid: int) -> ProcessAncestry:
        observed.append(pid)
        return _ancestry(pid)

    runner = ObservedProcessRunner(ancestry_reader=read_ancestry)
    argument = "& echo not-executed"
    result = runner.run(
        (sys.executable, "-c", "import sys; print(sys.argv[1])", argument),
        cwd=tmp_path,
        stdin=None,
        timeout_seconds=10.0,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == argument
    assert result.stderr == ""
    assert len(observed) == 1
    assert runner.observations[0].pid == observed[0]
    assert runner.observations[0].command[0] == sys.executable
    assert runner.observations[0].ancestry is not None
    assert runner.observations[0].ancestry.subject_pid == observed[0]


def test_preserves_stdin_and_nonzero_status(tmp_path: Path) -> None:
    runner = ObservedProcessRunner(ancestry_reader=_ancestry)
    result = runner.run(
        (sys.executable, "-c", "import sys; print(sys.stdin.read()); raise SystemExit(7)"),
        cwd=tmp_path,
        stdin="payload",
        timeout_seconds=10.0,
    )
    assert result.returncode == 7
    assert result.stdout.strip() == "payload"
    assert len(runner.observations) == 1


def test_timeout_terminates_process_and_is_recorded(tmp_path: Path) -> None:
    runner = ObservedProcessRunner(ancestry_reader=_ancestry)
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run(
            (sys.executable, "-c", "import time; time.sleep(5)"),
            cwd=tmp_path,
            stdin=None,
            timeout_seconds=0.05,
        )

    assert len(runner.observations) == 1
    assert runner.observations[0].timed_out is True


def test_short_unobserved_probe_does_not_depend_on_live_child_ancestry(
    tmp_path: Path,
) -> None:
    ancestry_calls: list[int] = []

    def vanished_child(pid: int) -> ProcessAncestry:
        ancestry_calls.append(pid)
        raise RuntimeError("child exited before CIM query")

    runner = ObservedProcessRunner(
        ancestry_reader=vanished_child,
        observe_command=lambda command: command[-1] != "--version",
    )
    result = runner.run(
        (sys.executable, "-c", "print('version')", "--version"),
        cwd=tmp_path,
        stdin=None,
        timeout_seconds=10.0,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "version"
    assert ancestry_calls == []
    assert runner.observations == ()


def test_live_launch_records_attempt_when_ancestry_capture_fails(
    tmp_path: Path,
) -> None:
    def unavailable_ancestry(pid: int) -> ProcessAncestry:
        del pid
        raise RuntimeError("synthetic CIM failure")

    runner = ObservedProcessRunner(ancestry_reader=unavailable_ancestry)
    with pytest.raises(RuntimeError, match="synthetic CIM failure"):
        runner.run(
            (sys.executable, "-c", "import time; time.sleep(5)"),
            cwd=tmp_path,
            stdin=None,
            timeout_seconds=10.0,
        )

    assert len(runner.observations) == 1
    observation = runner.observations[0]
    assert observation.pid > 0
    assert observation.ancestry is None
    assert observation.ancestry_error == "RuntimeError"
    assert observation.to_mapping()["ancestry_status"] == "unavailable"
    assert observation.timed_out is False
