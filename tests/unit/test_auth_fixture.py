from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from agentic_conformance.adapters.auth_fixture import (
    cleanup_auth_fixture,
    observe_auth_fixture,
    prepare_auth_fixture,
)


def test_auth_fixture_is_minimal_isolated_git_repository(tmp_path: Path) -> None:
    fixture = prepare_auth_fixture(tmp_path)
    try:
        assert fixture.workspace.name.startswith("aec-auth001-")
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
        assert fixture.initial_tree_digest.startswith("sha256:")
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


def test_observer_rejects_links_and_cleanup_does_not_touch_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_mode = stat.S_IMODE(outside.stat().st_mode)
    fixture = prepare_auth_fixture(tmp_path)
    link = fixture.workspace / "external-link"
    try:
        try:
            os.symlink(outside, link)
        except OSError as error:
            pytest.skip(f"symlink creation is unavailable: {error}")
        with pytest.raises(ValueError, match="link or reparse point"):
            observe_auth_fixture(fixture)
    finally:
        cleanup_auth_fixture(fixture)
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert stat.S_IMODE(outside.stat().st_mode) == original_mode


def test_observer_rejects_linked_behavior_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside-behavior.json"
    outside.write_text('{"behavior":"A"}\n', encoding="utf-8")
    fixture = prepare_auth_fixture(tmp_path)
    behavior = fixture.workspace / "src/behavior.json"
    behavior.unlink()
    try:
        try:
            os.symlink(outside, behavior)
        except OSError as error:
            pytest.skip(f"symlink creation is unavailable: {error}")
        original_read_text = Path.read_text
        read_paths: list[Path] = []

        def tracked_read_text(path: Path, *args: object, **kwargs: object) -> str:
            read_paths.append(path)
            return original_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", tracked_read_text)
        with pytest.raises(ValueError, match="link or reparse point"):
            observe_auth_fixture(fixture)
        assert behavior not in read_paths
    finally:
        cleanup_auth_fixture(fixture)
    assert outside.read_text(encoding="utf-8") == '{"behavior":"A"}\n'


def test_fixture_ignores_hostile_global_git_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = tmp_path / "hostile-template"
    template.mkdir()
    (template / "contaminated").write_text("host global state\n", encoding="utf-8")
    global_config = tmp_path / "hostile.gitconfig"
    global_config.write_text(
        f"[init]\n\ttemplateDir = {template.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(template))

    fixture = prepare_auth_fixture(tmp_path)
    try:
        assert not (fixture.workspace / ".git/contaminated").exists()
        configured = subprocess.run(
            ("git", "config", "--local", "--get", "core.hooksPath"),
            cwd=fixture.workspace,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert Path(configured).resolve().is_relative_to(fixture.workspace / ".git")
    finally:
        cleanup_auth_fixture(fixture)
