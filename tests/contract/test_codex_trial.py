from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_conformance import trial_persistence
from agentic_conformance.adapters.auth_fixture import AuthTreatment
from agentic_conformance.adapters.codex import CodexAdapter
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.codex_trial import (
    _fixture_version,
    run_auth_calibration_trial,
    run_auth_trial,
)
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.scenario import load_scenario

ROOT = Path(__file__).parents[2]


def test_fixture_version_is_bound_to_ground_truth_not_scenario_version() -> None:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    assert _fixture_version(replace(scenario, version="2.0.0")) == "1.0.0"


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
                '{"type":"item.completed","item":{"id":"m1","type":"agent_message","text":"private-agent-text"}}\n'
                '{"type":"turn.completed","usage":{"output_tokens":1}}\n'
            )
        return ProcessResult(0, stdout, "", "2026-08-27T00:00:00Z", "2026-08-27T00:00:01Z")


def test_trial_persists_schema_valid_closed_rescorable_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-persisted")
    events: list[str] = []
    process = TrialProcessRunner(events)
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path / "workspaces",
        before_execute=lambda _: events.append("preflight"),
    )

    artifacts = run_auth_trial(
        tmp_path / "runs",
        adapter,
        run_id="planned-codex-1",
        additional_diagnostics={"process-ancestry.json": '{"safe":true}\n'},
    )

    assert events == ["preflight", "execute"]
    assert artifacts.run_id == "planned-codex-1"
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
    persisted = artifacts.evidence_path.read_text(encoding="utf-8")
    evidence = EvidenceBundle.from_json(persisted)
    event_log = evidence.artifacts_of_kind("codex_event_log")[0]
    assert "private-agent-text" not in json.dumps(event_log.data)
    assert evidence.artifacts_of_kind("codex_agent_message")[0].level.value == "E4"
    assert "must-not-be-persisted" not in persisted
    assert "must-not-be-persisted" not in artifacts.manifest_path.read_text(encoding="utf-8")
    assert all(item["path"] == "evidence.json" for item in manifest["evidence"])


def test_trial_cleans_staging_directory_when_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = TrialProcessRunner([])
    adapter = CodexAdapter(
        process_runner=process,
        executable_resolver=lambda _: "codex",
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


def test_calibration_trial_persists_separate_v2_result(tmp_path: Path) -> None:
    adapter = CodexAdapter(
        process_runner=TrialProcessRunner([]),
        executable_resolver=lambda _: "codex",
        workspace_parent=tmp_path / "workspaces",
        treatment=AuthTreatment.CALIBRATION,
    )

    artifacts = run_auth_calibration_trial(tmp_path / "runs", adapter, run_id="planned-codex-cal-1")

    assert artifacts.result.classification.value == "CALIBRATION_PASS"
    assert artifacts.result == artifacts.rescored
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    assert manifest["scenario"]["version"] == "2.0.0"
    assert manifest["fixture_version"] == "1.0.0"
    assert manifest["treatment"] == "CALIBRATION"
