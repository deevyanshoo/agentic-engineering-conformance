from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_conformance import trial_persistence
from agentic_conformance.adapters.claude import ClaudeAdapter
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.claude_trial import run_auth_trial
from agentic_conformance.evidence import EvidenceBundle

ROOT = Path(__file__).parents[2]


class TrialProcessRunner:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls = 0

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del stdin, timeout_seconds
        self.calls += 1
        if command[-1] == "--version":
            stdout = "2.1.236 (Claude Code)\n"
        elif command[-3:] == ("auth", "status", "--json"):
            stdout = '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"}'
        else:
            self.events.append("execute")
            assert cwd is not None
            (cwd / "src/behavior.json").write_text('{"behavior":"B"}\n', encoding="utf-8")
            stdout = (
                '{"type":"system","subtype":"init","session_id":"session-contract","model":"claude-sonnet-test"}\n'
                '{"type":"assistant","session_id":"session-contract","message":{"model":"claude-sonnet-test","content":[{"type":"text","text":"private-agent-text"}]}}\n'
                '{"type":"result","subtype":"success","session_id":"session-contract","result":"private-agent-text","usage":{"output_tokens":1}}\n'
            )
        return ProcessResult(
            0,
            stdout,
            "",
            "2026-08-28T00:00:00Z",
            "2026-08-28T00:00:01Z",
        )


def test_trial_persists_schema_valid_closed_rescorable_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_AUTH_TOKEN", "must-not-be-persisted")
    events: list[str] = []
    process = TrialProcessRunner(events)
    adapter = ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path / "workspaces",
        before_execute=lambda _: events.append("preflight"),
    )

    artifacts = run_auth_trial(
        tmp_path / "runs",
        adapter,
        run_id="planned-claude-1",
        additional_diagnostics={"process-ancestry.json": '{"safe":true}\n'},
    )

    assert events == ["preflight", "execute"]
    assert artifacts.run_id == "planned-claude-1"
    assert artifacts.result == artifacts.rescored
    assert process.calls == 3
    assert artifacts.evidence_path.exists()
    assert artifacts.manifest_path.exists()
    assert artifacts.raw_jsonl_path.exists()
    assert "private-agent-text" in artifacts.raw_jsonl_path.read_text(encoding="utf-8")
    assert (artifacts.output_directory / "process-ancestry.json").read_text(
        encoding="utf-8"
    ) == '{"safe":true}\n'

    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/run.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    assert manifest["stack"]["name"] == "Anthropic Claude Code"
    assert manifest["model_identifier"] == "claude-sonnet-test"

    persisted = artifacts.evidence_path.read_text(encoding="utf-8")
    evidence = EvidenceBundle.from_json(persisted)
    event_log = evidence.artifacts_of_kind("claude_event_log")[0]
    assert "private-agent-text" not in json.dumps(event_log.data)
    assert evidence.artifacts_of_kind("claude_agent_message")[0].level.value == "E4"
    assert "must-not-be-persisted" not in persisted
    assert "must-not-be-persisted" not in artifacts.manifest_path.read_text(encoding="utf-8")
    assert all(item["path"] == "evidence.json" for item in manifest["evidence"])


def test_trial_cleans_staging_directory_when_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = ClaudeAdapter(
        process_runner=TrialProcessRunner([]),
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path / "workspaces",
    )

    def fail_validation(value: object, path: Path) -> None:
        del value, path
        raise ValueError("synthetic schema failure")

    monkeypatch.setattr(trial_persistence, "_validate_schema", fail_validation)
    output_root = tmp_path / "runs"
    with pytest.raises(ValueError, match="synthetic schema failure"):
        run_auth_trial(output_root, adapter)
    assert not output_root.exists() or not list(output_root.iterdir())
