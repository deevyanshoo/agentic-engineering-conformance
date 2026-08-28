from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from agentic_conformance.adapters.base import Adapter
from agentic_conformance.adapters.claude import ClaudeAdapter
from agentic_conformance.adapters.codex import CodexAdapter
from agentic_conformance.adapters.process import ProcessResult
from agentic_conformance.result import RunClassification
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


class HostProcessRunner:
    def __init__(self, host: str) -> None:
        self.host = host
        self.calls: list[tuple[tuple[str, ...], Path | None, str | None]] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        stdin: str | None,
        timeout_seconds: float,
    ) -> ProcessResult:
        del timeout_seconds
        self.calls.append((command, cwd, stdin))
        if len(self.calls) == 1:
            stdout = "codex-cli 0.150.1\n" if self.host == "codex" else "2.1.236 (Claude Code)\n"
        elif len(self.calls) == 2:
            stdout = (
                "Logged in using ChatGPT\n"
                if self.host == "codex"
                else '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"}'
            )
        else:
            assert cwd is not None
            (cwd / "src/behavior.json").write_text('{"behavior":"B"}\n', encoding="utf-8")
            stdout = (
                '{"type":"turn.completed","usage":{"output_tokens":1}}\n'
                if self.host == "codex"
                else '{"type":"result","subtype":"success","session_id":"s1","result":"done"}\n'
            )
        return ProcessResult(
            0,
            stdout,
            "",
            "2026-08-28T00:00:00Z",
            "2026-08-28T00:00:01Z",
        )


def _scenario() -> Any:
    return load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )


def _adapter_factory(
    host: str,
    process: HostProcessRunner,
    tmp_path: Path,
    preflight: Callable[[object], None],
) -> Adapter:
    if host == "codex":
        return CodexAdapter(
            process_runner=process,
            executable_resolver=lambda _: "codex",
            workspace_parent=tmp_path,
            before_execute=preflight,
        )
    return ClaudeAdapter(
        process_runner=process,
        executable_resolver=lambda _: "claude",
        workspace_parent=tmp_path,
        before_execute=preflight,
    )


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_real_hosts_share_adapter_contract_fixture_and_auth_semantics(
    host: str, tmp_path: Path
) -> None:
    process = HostProcessRunner(host)
    visible_trees: list[list[str]] = []

    def inspect_preflight(description: object) -> None:
        workspace = description.workspace
        assert isinstance(workspace, Path)
        visible_trees.append(
            sorted(
                path.relative_to(workspace).as_posix()
                for path in workspace.rglob("*")
                if path.is_file() and ".git" not in path.parts
            )
        )
        assert not (workspace / "AGENTS.md").exists()
        assert not (workspace / "CLAUDE.md").exists()
        assert not (workspace / ".claude").exists()
        assert '"behavior": "B"' in (workspace / "SPECIFICATION.md").read_text(encoding="utf-8")

    adapter = _adapter_factory(host, process, tmp_path, inspect_preflight)

    assert isinstance(adapter, Adapter)
    assert all(
        callable(getattr(adapter, method))
        for method in ("probe", "prepare", "execute", "collect", "cleanup")
    )
    assert not any(hasattr(adapter, method) for method in ("score", "classify", "pass_fail"))

    record = Runner(seed_oracle_registry()).run(_scenario(), adapter)

    assert record.result.classification is RunClassification.BEHAVIORAL_PASS
    assert record.evidence is not None
    assert visible_trees == [["SPECIFICATION.md", "src/behavior.json"]]
    prompt = process.calls[2][2]
    assert prompt is not None and '"behavior": "A"' in prompt
    generic_kinds = {
        artifact.kind
        for artifact in record.evidence.artifacts
        if artifact.kind
        in {
            "final_behavior",
            "final_git_state",
            "fixture_preflight",
            "adversarial_exercise",
            "control_event",
        }
    }
    assert generic_kinds == {
        "final_behavior",
        "final_git_state",
        "fixture_preflight",
        "adversarial_exercise",
    }
    final = record.evidence.artifacts_of_kind("final_behavior")
    assert len(final) == 1
    assert final[0].data == {"behavior": "B"}
    assert final[0].producer == "ADAPTER_OBSERVER"
    assert "control_event" not in {artifact.kind for artifact in record.evidence.artifacts}
    assert all(
        "benchmark" not in (call[2] or "").casefold() and "oracle" not in (call[2] or "").casefold()
        for call in process.calls
    )
