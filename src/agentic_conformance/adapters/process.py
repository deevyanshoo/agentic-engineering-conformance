from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    started_at: str
    ended_at: str


class ProcessRunner(Protocol):
    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult: ...


class SubprocessRunner:
    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        started_at = utc_now()
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=stdin,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
        return ProcessResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
            started_at,
            utc_now(),
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
