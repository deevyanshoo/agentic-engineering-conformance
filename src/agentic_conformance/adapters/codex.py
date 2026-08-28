from __future__ import annotations

import json
import re
import shutil
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_conformance.adapters.auth_fixture import (
    AuthFinalState,
    AuthFixture,
    cleanup_auth_fixture,
    observe_auth_fixture,
    prepare_auth_fixture,
)
from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.adapters.process import ProcessResult, ProcessRunner, SubprocessRunner
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import Scenario


@dataclass(frozen=True, slots=True)
class CodexEvent:
    event_type: str
    category: str
    item_type: str | None
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ParsedCodexJsonl:
    events: tuple[CodexEvent, ...]
    raw_events: tuple[dict[str, Any], ...]
    thread_id: str | None
    final_message: str | None
    usage: dict[str, int] | None


@dataclass(frozen=True, slots=True)
class CodexRunDescription:
    cli_version: str
    command: tuple[str, ...]
    workspace: Path
    model: str
    reasoning_effort: str
    service_tier: str
    sandbox: str
    shell_network: bool
    user_config_ignored: bool
    repository_rules_ignored: bool


@dataclass(frozen=True, slots=True)
class CodexRunObservation:
    description: CodexRunDescription
    initial_head: str
    final_state: AuthFinalState
    process: ProcessResult
    thread_id: str | None
    usage: Mapping[str, int] | None


@dataclass(slots=True)
class _RunState:
    scenario: Scenario
    fixture: AuthFixture
    description: CodexRunDescription
    process: ProcessResult | None = None
    parsed: ParsedCodexJsonl | None = None


def parse_codex_jsonl(value: str) -> ParsedCodexJsonl:
    raw_events: list[dict[str, Any]] = []
    events: list[CodexEvent] = []
    thread_id: str | None = None
    final_message: str | None = None
    usage: dict[str, int] | None = None
    for line_number, line in enumerate(value.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Codex JSONL line {line_number} is malformed") from error
        if not isinstance(parsed, dict):
            raise ValueError(f"Codex JSONL line {line_number} is not an object")
        raw: dict[str, Any] = json.loads(
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        raw_events.append(raw)
        raw_type = raw.get("type")
        event_type: str = raw_type if isinstance(raw_type, str) else "unknown"
        category = _event_category(event_type)
        metadata: dict[str, Any] = {}
        item_type: str | None = None
        if event_type == "thread.started" and isinstance(raw.get("thread_id"), str):
            thread_id = raw["thread_id"]
            metadata["thread_id"] = thread_id
        item = raw.get("item")
        if isinstance(item, dict):
            if isinstance(item.get("type"), str):
                item_type = item["type"]
                metadata["item_type"] = item_type
            if isinstance(item.get("id"), str):
                metadata["item_id"] = item["id"]
            if item_type == "agent_message" and isinstance(item.get("text"), str):
                final_message = item["text"]
        raw_usage = raw.get("usage")
        if isinstance(raw_usage, dict) and all(
            isinstance(key, str) and isinstance(amount, int) for key, amount in raw_usage.items()
        ):
            usage = dict(raw_usage)
            metadata["usage"] = dict(raw_usage)
        events.append(CodexEvent(event_type, category, item_type, metadata))
    return ParsedCodexJsonl(tuple(events), tuple(raw_events), thread_id, final_message, usage)


def _event_category(event_type: str) -> str:
    prefix = event_type.split(".", maxsplit=1)[0]
    return prefix if prefix in {"thread", "turn", "item", "error"} else "unknown"


class CodexAdapter(Adapter):
    """Launch and passively observe Codex CLI without adding engineering controls."""

    name = "codex"
    version = "0.2.0"

    def __init__(
        self,
        *,
        process_runner: ProcessRunner | None = None,
        executable_resolver: Callable[[str], str | None] = shutil.which,
        workspace_parent: Path | None = None,
        timeout_seconds: float = 300.0,
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "high",
        service_tier: str = "default",
        before_execute: Callable[[CodexRunDescription], None] | None = None,
    ) -> None:
        self._process_runner = process_runner or SubprocessRunner()
        self._executable_resolver = executable_resolver
        self._workspace_parent = workspace_parent
        self._timeout_seconds = timeout_seconds
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._service_tier = service_tier
        self._before_execute = before_execute
        self._executable: str | None = None
        self._cli_version: str | None = None
        self._probed_capabilities: frozenset[str] | None = None
        self._runs: dict[str, _RunState] = {}
        self.last_observation: CodexRunObservation | None = None

    def probe(self) -> frozenset[str]:
        if self._probed_capabilities is not None:
            return self._probed_capabilities
        executable = self._executable_resolver("codex")
        if executable is None:
            self._probed_capabilities = frozenset()
            return self._probed_capabilities
        version_result = self._process_runner.run(
            (executable, "--version"), cwd=None, stdin=None, timeout_seconds=30.0
        )
        if version_result.returncode != 0:
            raise RuntimeError("Codex CLI version probe failed")
        match = re.fullmatch(r"codex-cli\s+(\d+\.\d+\.\d+)\s*", version_result.stdout)
        if match is None:
            raise ValueError("Codex CLI version output is malformed")
        login_result = self._process_runner.run(
            (executable, "login", "status"), cwd=None, stdin=None, timeout_seconds=30.0
        )
        self._executable = executable
        self._cli_version = match.group(1)
        if login_result.returncode == 0:
            self._probed_capabilities = frozenset({"filesystem.read", "filesystem.write"})
        elif "not logged in" in (login_result.stdout + login_result.stderr).casefold():
            self._probed_capabilities = frozenset()
        else:
            raise RuntimeError("Codex CLI login status probe failed")
        return self._probed_capabilities

    def prepare(self, scenario: Scenario) -> PreparedRun:
        if scenario.scenario_id != "AUTH-001":
            raise ValueError("Codex M2 adapter supports only AUTH-001")
        if self._executable is None or self._cli_version is None:
            raise RuntimeError("Codex adapter must be successfully probed before prepare")
        fixture = prepare_auth_fixture(self._workspace_parent)
        command = self._command(fixture.workspace)
        description = CodexRunDescription(
            cli_version=self._cli_version,
            command=command,
            workspace=fixture.workspace,
            model=self._model,
            reasoning_effort=self._reasoning_effort,
            service_tier=self._service_tier,
            sandbox="workspace-write",
            shell_network=False,
            user_config_ignored=True,
            repository_rules_ignored=True,
        )
        token = str(uuid.uuid4())
        self._runs[token] = _RunState(scenario, fixture, description)
        return PreparedRun(token)

    def execute(self, prepared: PreparedRun) -> None:
        state = self._state(prepared)
        if self._before_execute is not None:
            self._before_execute(state.description)
        process = self._process_runner.run(
            state.description.command,
            cwd=state.fixture.workspace,
            stdin=state.fixture.prompt,
            timeout_seconds=self._timeout_seconds,
        )
        state.process = process
        if process.returncode != 0:
            raise RuntimeError(f"Codex execution failed with exit status {process.returncode}")
        state.parsed = parse_codex_jsonl(process.stdout)

    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        state = self._state(prepared)
        if state.process is None or state.parsed is None:
            raise RuntimeError("Codex run has not completed")
        final_state = observe_auth_fixture(state.fixture)
        subject = scenario_digest(state.scenario)
        artifacts: list[EvidenceArtifact] = []
        if final_state.behavior is not None:
            artifacts.append(
                _artifact(
                    "codex-final-behavior",
                    EvidenceLevel.E1,
                    "final_behavior",
                    "ADAPTER_OBSERVER",
                    {"behavior": final_state.behavior},
                    subject,
                )
            )
        artifacts.extend(
            (
                _artifact(
                    "codex-final-git-state",
                    EvidenceLevel.E1,
                    "final_git_state",
                    "ADAPTER_OBSERVER",
                    {
                        "initial_head": state.fixture.initial_head,
                        "head": final_state.head,
                        "status": list(final_state.status),
                        "diff": final_state.diff,
                        "tree_digest": final_state.tree_digest,
                    },
                    subject,
                ),
                _artifact(
                    "codex-fixture-preflight",
                    EvidenceLevel.E1,
                    "fixture_preflight",
                    "ADAPTER_OBSERVER",
                    {
                        "readable": True,
                        "writable": True,
                        "initial_head": state.fixture.initial_head,
                        "initial_tree_digest": state.fixture.initial_tree_digest,
                    },
                    subject,
                ),
                _artifact(
                    "codex-process",
                    EvidenceLevel.E1,
                    "codex_process",
                    "ADAPTER_OBSERVER",
                    {
                        "cli_version": state.description.cli_version,
                        "command": list(state.description.command),
                        "returncode": state.process.returncode,
                        "started_at": state.process.started_at,
                        "ended_at": state.process.ended_at,
                    },
                    subject,
                ),
                _artifact(
                    "codex-adversarial-exercise",
                    EvidenceLevel.E1,
                    "adversarial_exercise",
                    "ADAPTER_OBSERVER",
                    {"condition": "stale_context_supplied"},
                    subject,
                ),
                _artifact(
                    "codex-event-log",
                    EvidenceLevel.E2,
                    "codex_event_log",
                    "CODEX_LIFECYCLE",
                    {"events": [_normalized_event(event) for event in state.parsed.events]},
                    subject,
                ),
            )
        )
        if state.parsed.final_message is not None:
            artifacts.append(
                _artifact(
                    "codex-agent-message",
                    EvidenceLevel.E4,
                    "codex_agent_message",
                    "AGENT",
                    {"message": state.parsed.final_message},
                    subject,
                )
            )
        self.last_observation = CodexRunObservation(
            state.description,
            state.fixture.initial_head,
            final_state,
            state.process,
            state.parsed.thread_id,
            state.parsed.usage,
        )
        return EvidenceBundle.create(
            state.scenario.scenario_id,
            state.scenario.version,
            subject,
            state.scenario.ground_truth,
            artifacts,
            (
                "User-global host instructions, skills/plugins, and outer policy may remain "
                "despite --ignore-user-config.",
                "Codex host API and authentication may require network access; "
                "target shell network is disabled.",
                "Codex JSONL is retained as diagnostic evidence and is not required by "
                "the AUTH-001 oracle.",
            ),
        )

    def cleanup(self, prepared: PreparedRun) -> None:
        state = self._runs.pop(prepared.token, None)
        if state is None:
            raise ValueError("unknown prepared run")
        cleanup_auth_fixture(state.fixture)

    def _state(self, prepared: PreparedRun) -> _RunState:
        try:
            return self._runs[prepared.token]
        except KeyError as error:
            raise ValueError("unknown prepared run") from error

    def _command(self, workspace: Path) -> tuple[str, ...]:
        if self._executable is None:
            raise RuntimeError("Codex executable is unavailable")
        return (
            self._executable,
            "exec",
            "--strict-config",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "workspace-write",
            "--model",
            self._model,
            "-c",
            'approval_policy="never"',
            "-c",
            f'model_reasoning_effort="{self._reasoning_effort}"',
            "-c",
            f'service_tier="{self._service_tier}"',
            "-c",
            "sandbox_workspace_write.network_access=false",
            "-c",
            'shell_environment_policy.inherit="core"',
            "-c",
            "shell_environment_policy.ignore_default_excludes=false",
            "-C",
            str(workspace),
            "-",
        )


def _artifact(
    artifact_id: str,
    level: EvidenceLevel,
    kind: str,
    producer: str,
    data: Mapping[str, Any],
    subject_digest: str,
) -> EvidenceArtifact:
    return EvidenceArtifact.create(
        artifact_id, level, kind, producer, data, subject_digest=subject_digest
    )


def _normalized_event(event: CodexEvent) -> dict[str, Any]:
    return {
        "type": event.event_type,
        "category": event.category,
        "item_type": event.item_type,
        "metadata": dict(event.metadata),
    }
