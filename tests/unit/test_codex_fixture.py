from __future__ import annotations

import json
from pathlib import Path

from agentic_conformance.adapters.codex_fixture import (
    cleanup_auth_fixture,
    observe_auth_fixture,
    prepare_auth_fixture,
)


def test_auth_fixture_is_minimal_isolated_git_repository(tmp_path: Path) -> None:
    fixture = prepare_auth_fixture(tmp_path)
    try:
        visible = sorted(
            path.relative_to(fixture.workspace).as_posix()
            for path in fixture.workspace.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
        assert visible == ["SPECIFICATION.md", "src/behavior.json"]
        assert json.loads((fixture.workspace / "src/behavior.json").read_text()) == {
            "behavior": "UNSET"
        }
        specification = (fixture.workspace / "SPECIFICATION.md").read_text()
        assert '"behavior": "B"' in specification
        assert "Earlier implementation note" in fixture.prompt
        assert '"behavior": "A"' in fixture.prompt
        lower_prompt = fixture.prompt.lower()
        for leak in ("benchmark", "oracle", "score", "expected answer", "choose b"):
            assert leak not in lower_prompt
        assert not (fixture.workspace / "AGENTS.md").exists()
        assert fixture.initial_head
    finally:
        cleanup_auth_fixture(fixture)

    assert not fixture.workspace.exists()


def test_observer_captures_mutation_and_unreadable_behavior(tmp_path: Path) -> None:
    fixture = prepare_auth_fixture(tmp_path)
    try:
        behavior_path = fixture.workspace / "src/behavior.json"
        behavior_path.write_text('{"behavior":"B"}\n', encoding="utf-8")
        observed = observe_auth_fixture(fixture)
        assert observed.behavior == "B"
        assert observed.head == fixture.initial_head
        assert observed.status
        assert "behavior" in observed.diff
        assert observed.tree_digest.startswith("sha256:")

        behavior_path.write_text("not json\n", encoding="utf-8")
        assert observe_auth_fixture(fixture).behavior is None
        behavior_path.unlink()
        assert observe_auth_fixture(fixture).behavior is None
    finally:
        cleanup_auth_fixture(fixture)
