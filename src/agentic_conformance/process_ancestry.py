from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from agentic_conformance.adapters.process import utc_now

_KNOWN_AGENT_MARKERS = ("codex", "claude", "cursor", "copilot", "gemini")
_SCHEDULER_NAMES = frozenset({"taskeng.exe", "taskhostw.exe", "svchost.exe"})


@dataclass(frozen=True, slots=True)
class ProcessNode:
    pid: int
    parent_pid: int
    name: str
    executable: str | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "parent_pid": self.parent_pid,
            "name": self.name,
            "executable": self.executable,
        }


@dataclass(frozen=True, slots=True)
class ProcessAncestry:
    subject_pid: int
    nodes: tuple[ProcessNode, ...]
    captured_at: str
    complete: bool
    cycle_detected: bool

    @classmethod
    def from_processes(
        cls, subject_pid: int, processes: tuple[ProcessNode, ...], captured_at: str
    ) -> ProcessAncestry:
        table = {process.pid: process for process in processes}
        if subject_pid not in table:
            raise ValueError("process ancestry subject is absent from the process table")
        nodes: list[ProcessNode] = []
        seen: set[int] = set()
        current = subject_pid
        complete = False
        cycle_detected = False
        while current in table:
            if current in seen:
                cycle_detected = True
                break
            seen.add(current)
            node = table[current]
            nodes.append(node)
            if node.parent_pid == 0:
                complete = True
                break
            current = node.parent_pid
        return cls(subject_pid, tuple(nodes), captured_at, complete, cycle_detected)

    def to_mapping(self) -> dict[str, object]:
        return {
            "subject_pid": self.subject_pid,
            "captured_at": self.captured_at,
            "complete": self.complete,
            "cycle_detected": self.cycle_detected,
            "nodes": [node.to_mapping() for node in self.nodes],
        }


@dataclass(frozen=True, slots=True)
class NeutralityDecision:
    valid: bool
    status: str
    reason: str


def assess_worker_neutrality(ancestry: ProcessAncestry) -> NeutralityDecision:
    if ancestry.cycle_detected:
        return NeutralityDecision(
            False, "INVALID_NEUTRAL_ENVIRONMENT", "process ancestry contains a cycle"
        )
    ancestors = ancestry.nodes[1:]
    for node in ancestors:
        identity = f"{node.name} {node.executable or ''}".casefold()
        if any(marker in identity for marker in _KNOWN_AGENT_MARKERS):
            return NeutralityDecision(
                False,
                "INVALID_NEUTRAL_ENVIRONMENT",
                f"known coding-agent ancestor observed: {node.name}",
            )
    if not any(node.name.casefold() in _SCHEDULER_NAMES for node in ancestors):
        return NeutralityDecision(
            False,
            "INVALID_NEUTRAL_ENVIRONMENT",
            "no Windows scheduler/service ancestor was observed",
        )
    return NeutralityDecision(True, "NEUTRAL_BASELINE", "scheduler ancestry observed")


def parse_process_table(value: str) -> tuple[ProcessNode, ...]:
    try:
        raw: Any = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("process table is not valid JSON") from error
    items = raw if isinstance(raw, list) else [raw]
    processes: list[ProcessNode] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("process table fields are malformed")
        pid = item.get("ProcessId")
        parent_pid = item.get("ParentProcessId")
        name = item.get("Name")
        executable = item.get("ExecutablePath")
        if (
            not isinstance(pid, int)
            or isinstance(pid, bool)
            or not isinstance(parent_pid, int)
            or isinstance(parent_pid, bool)
            or not isinstance(name, str)
            or (executable is not None and not isinstance(executable, str))
        ):
            raise ValueError("process table fields are malformed")
        processes.append(ProcessNode(pid, parent_pid, name, executable))
    return tuple(processes)


def capture_windows_ancestry(subject_pid: int) -> ProcessAncestry:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise RuntimeError("Windows PowerShell is unavailable for ancestry capture")
    script = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        (powershell, "-NoProfile", "-NonInteractive", "-Command", script),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=30.0,
    )
    if completed.returncode != 0:
        raise RuntimeError("Windows process ancestry query failed")
    return ProcessAncestry.from_processes(
        subject_pid, parse_process_table(completed.stdout), utc_now()
    )


def sanitized_environment() -> dict[str, str]:
    return {
        "os": os.name,
        "os_release": platform.release(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "machine": platform.machine(),
    }
