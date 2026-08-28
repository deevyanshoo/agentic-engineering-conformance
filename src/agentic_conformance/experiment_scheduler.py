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


@dataclass(frozen=True, slots=True)
class ScheduledTaskSpec:
    task_name: str
    execution_identity: str
    python_executable: Path
    working_directory: Path
    plan_path: Path
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
        arguments = subprocess.list2cmdline(
            ("-m", "agentic_conformance.experiment_worker", "--plan", str(plan))
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
            task_name, execution_identity, python, working, plan, created_at, arguments, digest
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
        ),
        claude=HostBinding(
            ClaudeAdapter.name,
            ClaudeAdapter.version,
            claude.probed_cli_version,
            str(Path(claude_path).resolve()),
            claude_description.requested_model,
            claude_config_digest(claude_description),
            "safe-mode;no-shell;no-web",
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
    plan_path: Path, *, timeout_seconds: float = 3600.0, poll_seconds: float = 10.0
) -> dict[str, object]:
    plan = load_plan(plan_path)
    identity = current_windows_identity()
    spec = ScheduledTaskSpec.create(
        task_name=f"AEC-M4-{plan.batch_id}",
        execution_identity=identity,
        python_executable=Path(sys.executable),
        working_directory=plan.source_root,
        plan_path=plan_path,
        created_at=utc_now(),
    )
    controller = SchedulerController()
    record_path = plan.output_root / "scheduler-record.json"
    record: dict[str, object] = {
        "schema_version": "0.1",
        "task_name": spec.task_name,
        "creation_time": spec.created_at,
        "execution_identity": identity,
        "command_digest": spec.command_digest,
        "registered": False,
        "started": False,
        "deletion_time": None,
        "cleanup_error": None,
    }
    registered = False
    try:
        xml_path = controller.register(spec)
        registered = True
        record["registered"] = True
        record["task_xml_digest"] = "sha256:" + hashlib.sha256(xml_path.read_bytes()).hexdigest()
        _atomic_json(record_path, record)
        controller.start(spec.task_name)
        record["started"] = True
        _atomic_json(record_path, record)
        marker = controller.wait(
            spec.task_name,
            plan.output_root / "batch-complete.json",
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
        record["terminal_status"] = marker.get("status")
        return marker
    except TimeoutError:
        if registered:
            controller.end(spec.task_name)
        raise
    finally:
        if registered:
            try:
                controller.delete(spec.task_name)
                record["deletion_time"] = utc_now()
            except Exception as error:
                record["cleanup_error"] = f"{type(error).__name__}: {error}"
        _atomic_json(record_path, record)


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
