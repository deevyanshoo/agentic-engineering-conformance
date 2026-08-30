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
    validate_auth_scenario,
)
from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.adapters.process import ProcessResult, ProcessRunner, SubprocessRunner
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import Scenario


@dataclass(frozen=True, slots=True)
class ClaudeEvent:
    event_type: str
    subtype: str | None
    category: str
    tool_events: tuple[Mapping[str, str | None], ...]
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ParsedClaudeJsonl:
    events: tuple[ClaudeEvent, ...]
    raw_events: tuple[dict[str, Any], ...]
    session_id: str | None
    model: str | None
    final_message: str | None
    usage: dict[str, int] | None


@dataclass(frozen=True, slots=True)
class ClaudeRunDescription:
    cli_version: str
    command: tuple[str, ...]
    workspace: Path
    requested_model: str
    output_format: str
    permission_mode: str
    tools: tuple[str, ...]
    safe_mode: bool
    session_persistence: bool
    target_shell_available: bool
    target_web_available: bool
    user_project_config_disabled: bool
    managed_policy_observable: bool


@dataclass(frozen=True, slots=True)
class ClaudeRunObservation:
    description: ClaudeRunDescription
    initial_head: str
    final_state: AuthFinalState
    process: ProcessResult
    session_id: str | None
    observed_model: str | None
    usage: Mapping[str, int] | None
    raw_events: tuple[dict[str, Any], ...]


@dataclass(slots=True)
class _RunState:
    scenario: Scenario
    fixture: AuthFixture
    description: ClaudeRunDescription
    process: ProcessResult | None = None
    parsed: ParsedClaudeJsonl | None = None


def parse_claude_jsonl(value: str) -> ParsedClaudeJsonl:
    raw_events: list[dict[str, Any]] = []
    events: list[ClaudeEvent] = []
    session_id: str | None = None
    model: str | None = None
    final_message: str | None = None
    usage: dict[str, int] | None = None
    result_seen = False

    for line_number, line in enumerate(value.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Claude JSONL line {line_number} is malformed") from error
        if not isinstance(parsed, dict):
            raise ValueError(f"Claude JSONL line {line_number} is not an object")
        raw: dict[str, Any] = json.loads(
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        raw_events.append(raw)

        raw_type = raw.get("type")
        event_type = raw_type if isinstance(raw_type, str) else "unknown"
        raw_subtype = raw.get("subtype")
        subtype = raw_subtype if isinstance(raw_subtype, str) else None
        category = _event_category(event_type)
        metadata: dict[str, Any] = {}
        tool_events: list[dict[str, str | None]] = []

        raw_session_id = raw.get("session_id")
        if isinstance(raw_session_id, str):
            session_id = raw_session_id
            metadata["session_id"] = raw_session_id

        raw_model = raw.get("model")
        if isinstance(raw_model, str):
            model = raw_model
            metadata["model"] = raw_model

        message = raw.get("message")
        if isinstance(message, dict):
            message_model = message.get("model")
            if isinstance(message_model, str):
                model = message_model
                metadata["model"] = message_model
            message_usage = _numeric_usage(message.get("usage"))
            if message_usage is not None:
                usage = message_usage
                metadata["usage"] = message_usage
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type == "tool_use":
                        tool_events.append(
                            {
                                "id": block.get("id") if isinstance(block.get("id"), str) else None,
                                "name": (
                                    block.get("name")
                                    if isinstance(block.get("name"), str)
                                    else None
                                ),
                                "status": "requested",
                            }
                        )
                    elif block_type == "tool_result":
                        is_error = block.get("is_error") is True
                        tool_events.append(
                            {
                                "id": (
                                    block.get("tool_use_id")
                                    if isinstance(block.get("tool_use_id"), str)
                                    else None
                                ),
                                "name": None,
                                "status": "failed" if is_error else "completed",
                            }
                        )
                    elif block_type == "text" and isinstance(block.get("text"), str):
                        final_message = block["text"]

        raw_usage = _numeric_usage(raw.get("usage"))
        if raw_usage is not None:
            usage = raw_usage
            metadata["usage"] = raw_usage

        if event_type == "result":
            if subtype != "success" or raw.get("is_error") is True:
                raise ValueError("Claude terminal result indicates failure")
            if "is_error" in raw and not isinstance(raw["is_error"], bool):
                raise ValueError("Claude terminal result is malformed")

        if isinstance(raw.get("is_error"), bool):
            metadata["is_error"] = raw["is_error"]
        if type(raw.get("num_turns")) is int:
            metadata["num_turns"] = raw["num_turns"]
        if event_type == "result":
            if isinstance(raw.get("result"), str):
                final_message = raw["result"]
            result_seen = True

        events.append(ClaudeEvent(event_type, subtype, category, tuple(tool_events), metadata))

    if not raw_events:
        raise ValueError("Claude JSONL is empty")
    if not result_seen:
        raise ValueError("Claude JSONL has no terminal result event")
    return ParsedClaudeJsonl(
        tuple(events),
        tuple(raw_events),
        session_id,
        model,
        final_message,
        usage,
    )


def _numeric_usage(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict) or not value:
        return None
    if not all(isinstance(key, str) and type(amount) is int for key, amount in value.items()):
        return None
    return dict(value)


def _event_category(event_type: str) -> str:
    return event_type if event_type in {"system", "assistant", "user", "result"} else "unknown"


class ClaudeAdapter(Adapter):
    """Launch and passively observe Claude Code without adding engineering controls."""

    name = "claude"
    version = "0.3.0"

    def __init__(
        self,
        *,
        process_runner: ProcessRunner | None = None,
        executable_resolver: Callable[[str], str | None] = shutil.which,
        workspace_parent: Path | None = None,
        timeout_seconds: float = 300.0,
        model: str = "sonnet",
        before_execute: Callable[[ClaudeRunDescription], None] | None = None,
    ) -> None:
        self._process_runner = process_runner or SubprocessRunner()
        self._executable_resolver = executable_resolver
        self._workspace_parent = workspace_parent
        self._timeout_seconds = timeout_seconds
        self._model = model
        self._before_execute = before_execute
        self._executable: str | None = None
        self._cli_version: str | None = None
        self._probed_capabilities: frozenset[str] | None = None
        self._runs: dict[str, _RunState] = {}
        self.last_observation: ClaudeRunObservation | None = None

    def probe(self) -> frozenset[str]:
        if self._probed_capabilities is not None:
            return self._probed_capabilities
        executable = self._executable_resolver("claude")
        if executable is None:
            self._probed_capabilities = frozenset()
            return self._probed_capabilities

        version_result = self._process_runner.run(
            (executable, "--version"), cwd=None, stdin=None, timeout_seconds=30.0
        )
        if version_result.returncode != 0:
            raise RuntimeError("Claude CLI version probe failed")
        match = re.fullmatch(
            r"(\d+\.\d+\.\d+)\s+\(Claude Code\)\s*",
            version_result.stdout,
        )
        if match is None:
            raise ValueError("Claude CLI version output is malformed")

        auth_result = self._process_runner.run(
            (executable, "auth", "status", "--json"),
            cwd=None,
            stdin=None,
            timeout_seconds=30.0,
        )
        if auth_result.returncode not in {0, 1}:
            raise RuntimeError("Claude authentication probe failed")
        try:
            auth: Any = json.loads(auth_result.stdout)
        except json.JSONDecodeError as error:
            raise ValueError("Claude authentication output is malformed") from error
        if not isinstance(auth, dict) or not isinstance(auth.get("loggedIn"), bool):
            raise ValueError("Claude authentication output is malformed")

        self._executable = executable
        self._cli_version = match.group(1)
        if auth["loggedIn"]:
            if auth_result.returncode != 0:
                raise RuntimeError("Claude authentication probe failed")
            self._probed_capabilities = frozenset({"filesystem.read", "filesystem.write"})
        else:
            self._probed_capabilities = frozenset()
        return self._probed_capabilities

    def prepare(self, scenario: Scenario) -> PreparedRun:
        validate_auth_scenario(scenario)
        if self._executable is None or self._cli_version is None:
            raise RuntimeError("Claude adapter must be successfully probed before prepare")

        fixture = prepare_auth_fixture(self._workspace_parent)
        tools = ("Read", "Edit", "Write", "Glob", "Grep")
        description = ClaudeRunDescription(
            cli_version=self._cli_version,
            command=self._command(tools),
            workspace=fixture.workspace,
            requested_model=self._model,
            output_format="stream-json",
            permission_mode="acceptEdits",
            tools=tools,
            safe_mode=True,
            session_persistence=False,
            target_shell_available=False,
            target_web_available=False,
            user_project_config_disabled=True,
            managed_policy_observable=False,
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
            raise RuntimeError(f"Claude execution failed with exit status {process.returncode}")
        state.parsed = parse_claude_jsonl(process.stdout)

    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        state = self._state(prepared)
        if state.process is None or state.parsed is None:
            raise RuntimeError("Claude run has not completed")

        final_state = observe_auth_fixture(state.fixture)
        subject = scenario_digest(state.scenario)
        artifacts: list[EvidenceArtifact] = []
        if final_state.behavior is not None:
            artifacts.append(
                _artifact(
                    "claude-final-behavior",
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
                    "claude-final-git-state",
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
                    "claude-fixture-preflight",
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
                    "claude-process",
                    EvidenceLevel.E1,
                    "claude_process",
                    "ADAPTER_OBSERVER",
                    {
                        "cli_version": state.description.cli_version,
                        "command": list(state.description.command),
                        "requested_model": state.description.requested_model,
                        "observed_model": state.parsed.model,
                        "returncode": state.process.returncode,
                        "started_at": state.process.started_at,
                        "ended_at": state.process.ended_at,
                    },
                    subject,
                ),
                _artifact(
                    "claude-adversarial-exercise",
                    EvidenceLevel.E1,
                    "adversarial_exercise",
                    "ADAPTER_OBSERVER",
                    {"condition": "stale_context_supplied"},
                    subject,
                ),
                _artifact(
                    "claude-event-log",
                    EvidenceLevel.E2,
                    "claude_event_log",
                    "CLAUDE_LIFECYCLE",
                    {"events": [_normalized_event(event) for event in state.parsed.events]},
                    subject,
                ),
            )
        )
        if state.parsed.final_message is not None:
            artifacts.append(
                _artifact(
                    "claude-agent-message",
                    EvidenceLevel.E4,
                    "claude_agent_message",
                    "AGENT",
                    {"message": state.parsed.final_message},
                    subject,
                )
            )

        self.last_observation = ClaudeRunObservation(
            state.description,
            state.fixture.initial_head,
            final_state,
            state.process,
            state.parsed.session_id,
            state.parsed.model,
            state.parsed.usage,
            state.parsed.raw_events,
        )
        return EvidenceBundle.create(
            state.scenario.scenario_id,
            state.scenario.version,
            subject,
            state.scenario.ground_truth,
            artifacts,
            (
                "Claude safe mode disables user/project customizations, but administrator-managed "
                "policy may still apply.",
                "Claude host authentication/model access requires network; the target tool set "
                "excludes Bash and web tools.",
                "Claude stream JSON is diagnostic and is not required by the AUTH-001 oracle.",
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

    def _command(self, tools: tuple[str, ...]) -> tuple[str, ...]:
        if self._executable is None:
            raise RuntimeError("Claude executable is unavailable")
        return (
            self._executable,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--safe-mode",
            "--no-session-persistence",
            "--no-chrome",
            "--model",
            self._model,
            "--permission-mode",
            "acceptEdits",
            "--tools",
            ",".join(tools),
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
        artifact_id,
        level,
        kind,
        producer,
        data,
        subject_digest=subject_digest,
    )


def _normalized_event(event: ClaudeEvent) -> dict[str, Any]:
    return {
        "type": event.event_type,
        "subtype": event.subtype,
        "category": event.category,
        "tool_events": [dict(tool_event) for tool_event in event.tool_events],
        "metadata": dict(event.metadata),
    }
