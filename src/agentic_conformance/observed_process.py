from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from agentic_conformance.adapters.process import (
    ProcessResult,
    ProcessRunner,
    SubprocessRunner,
    utc_now,
)
from agentic_conformance.process_ancestry import (
    ProcessAncestry,
    capture_windows_ancestry,
)


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    pid: int
    command: tuple[str, ...]
    ancestry: ProcessAncestry | None
    ancestry_error: str | None
    timed_out: bool

    def to_mapping(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "command": list(self.command),
            "ancestry_status": "captured" if self.ancestry is not None else "unavailable",
            "ancestry": self.ancestry.to_mapping() if self.ancestry is not None else None,
            "ancestry_error": self.ancestry_error,
            "timed_out": self.timed_out,
        }


class ObservedProcessRunner:
    """Subprocess seam with passive, allowlisted process-ancestry observation."""

    def __init__(
        self,
        *,
        ancestry_reader: Callable[[int], ProcessAncestry] = capture_windows_ancestry,
        observe_command: Callable[[tuple[str, ...]], bool] = lambda _: True,
        unobserved_runner: ProcessRunner | None = None,
    ) -> None:
        self._ancestry_reader = ancestry_reader
        self._observe_command = observe_command
        self._unobserved_runner = unobserved_runner or SubprocessRunner()
        self._observations: list[ProcessObservation] = []

    @property
    def observations(self) -> tuple[ProcessObservation, ...]:
        return tuple(self._observations)

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        if not self._observe_command(command):
            return self._unobserved_runner.run(
                command,
                cwd=cwd,
                stdin=stdin,
                timeout_seconds=timeout_seconds,
            )
        started_at = utc_now()
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE if stdin is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        try:
            ancestry = self._ancestry_reader(process.pid)
        except Exception as error:
            self._observations.append(
                ProcessObservation(
                    process.pid,
                    command,
                    None,
                    type(error).__name__,
                    False,
                )
            )
            process.kill()
            process.communicate()
            raise
        observation = ProcessObservation(process.pid, command, ancestry, None, False)
        try:
            stdout, stderr = process.communicate(stdin, timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            process.kill()
            stdout, stderr = process.communicate()
            self._observations.append(replace(observation, timed_out=True))
            raise subprocess.TimeoutExpired(
                command, timeout_seconds, output=stdout, stderr=stderr
            ) from error
        self._observations.append(observation)
        return ProcessResult(process.returncode, stdout, stderr, started_at, utc_now())
