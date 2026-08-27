from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_conformance.adapters.codex import CodexAdapter, ProcessResult
from agentic_conformance.codex_trial import run_auth_trial

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
            stdout = "codex-cli 0.150.1\n"
        elif command[-2:] == ("login", "status"):
            stdout = "Logged in using ChatGPT\n"
        else:
            self.events.append("execute")
            assert cwd is not None
            (cwd / "src/behavior.json").write_text('{"behavior":"B"}\n', encoding="utf-8")
            stdout = (
                '{"type":"thread.started","thread_id":"thread-contract"}\n'
                '{"type":"turn.completed","usage":{"output_tokens":1}}\n'
            )
        return ProcessResult(0, stdout, "", "2026-08-27T00:00:00Z", "2026-08-27T00:00:01Z")


def test_trial_persists_schema_valid_closed_rescorable_evidence(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-persisted")  # type: ignore[attr-defined]
    events: list[str] = []
    process = TrialProcessRunner(events)
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path / "workspaces",
        before_execute=lambda _: events.append("preflight"),
    )

    artifacts = run_auth_trial(tmp_path / "runs", adapter)

    assert events == ["preflight", "execute"]
    assert artifacts.result == artifacts.rescored
    assert process.calls == 3
    assert artifacts.evidence_path.exists()
    assert artifacts.manifest_path.exists()
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/run.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    persisted = artifacts.evidence_path.read_text(encoding="utf-8")
    assert "must-not-be-persisted" not in persisted
    assert "must-not-be-persisted" not in artifacts.manifest_path.read_text(encoding="utf-8")
    assert all(item["path"] == "evidence.json" for item in manifest["evidence"])
