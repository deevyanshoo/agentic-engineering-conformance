from __future__ import annotations

from pathlib import Path

from agentic_conformance.adapters.claude import ClaudeAdapter
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.runner import Runner, rescore
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


class MutatingProcessRunner:
    def __init__(self) -> None:
        self.call_count = 0

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del stdin, timeout_seconds
        self.call_count += 1
        if command[-1] == "--version":
            stdout = "2.1.236 (Claude Code)\n"
        elif command[-3:] == ("auth", "status", "--json"):
            stdout = '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"}'
        else:
            assert cwd is not None
            (cwd / "src/behavior.json").write_text('{"behavior":"B"}\n', encoding="utf-8")
            stdout = (
                '{"type":"system","subtype":"init","session_id":"s1","model":"claude-sonnet-test"}\n'
                '{"type":"result","subtype":"success","session_id":"s1","result":"done"}\n'
            )
        return ProcessResult(
            0,
            stdout,
            "",
            "2026-08-28T00:00:00Z",
            "2026-08-28T00:00:01Z",
        )


def test_stored_claude_evidence_rescores_without_process_execution(tmp_path: Path) -> None:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    process = MutatingProcessRunner()
    adapter = ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
    )
    oracles = seed_oracle_registry()
    record = Runner(oracles).run(scenario, adapter)
    assert record.evidence is not None
    stored = record.evidence.to_json()
    calls_after_execution = process.call_count

    reloaded = EvidenceBundle.from_json(stored)
    rescored = rescore(scenario, reloaded, oracles)

    assert rescored == record.result
    assert process.call_count == calls_after_execution == 3
