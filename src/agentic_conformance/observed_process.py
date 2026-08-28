from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from agentic_conformance.adapters.process import ProcessResult, utc_now
from agentic_conformance.process_ancestry import (
    ProcessAncestry,
    capture_windows_ancestry,
)


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    pid: int
    command: tuple[str, ...]
    ancestry: ProcessAncestry
    timed_out: bool

    def to_mapping(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "command": list(self.command),
            "ancestry": self.ancestry.to_mapping(),
            "timed_out": self.timed_out,
        }


class ObservedProcessRunner:
    """Subprocess seam with passive, allowlisted process-ancestry observation."""

    def __init__(
        self, *, ancestry_reader: Callable[[int], ProcessAncestry] = capture_windows_ancestry
    ) -> None:
        self._ancestry_reader = ancestry_reader
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
        except Exception:
            process.kill()
            process.communicate()
            raise
        observation = ProcessObservation(process.pid, command, ancestry, False)
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
