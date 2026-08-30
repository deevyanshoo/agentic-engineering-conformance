from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from agentic_conformance.experiment_plan import load_plan
from agentic_conformance.experiment_worker import run_experiment

WINDOWS_REPRESENTATIVE_DIGEST = (
    "sha256:6977468641764e4629814d037d41ebf92f1ebec597ef384c21919015738b16ab"
)


def _digest(value: Mapping[str, object]) -> str:
    payload = {key: item for key, item in value.items() if key != "plan_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def _plan_mapping(origin: str) -> dict[str, object]:
    if origin == "windows":
        source_root = r"C:\aec"
        output_root = r"C:\aec\reports\runs\portable-plan"
        codex_executable = r"C:\tools\codex.CMD"
        claude_executable = r"\\host\tools\claude.CMD"
    elif origin == "posix":
        source_root = "/srv/aec"
        output_root = "/srv/aec/reports/runs/portable-plan"
        codex_executable = "/opt/aec/bin/codex"
        claude_executable = "/opt/aec/bin/claude"
    else:
        raise AssertionError(f"unsupported test origin: {origin}")
    value: dict[str, object] = {
        "schema_version": "0.1",
        "batch_id": "portable-plan",
        "label": "NEUTRAL_AUTONOMOUS_BASELINE",
        "benchmark_revision": "a" * 40,
        "source_root": source_root,
        "output_root": output_root,
        "scenario": {
            "id": "AUTH-001",
            "version": "1.0.0",
            "digest": "sha256:" + "b" * 64,
        },
        "fixture": {
            "version": "1.0.0",
            "digest": "sha256:" + "c" * 64,
        },
        "observation_mode": "BLACK_BOX",
        "network_policy": "RESTRICTED",
        "retry_limit": 0,
        "randomization": "alternating-codex-first-v1",
        "created_at": "2026-08-30T12:00:00Z",
        "hosts": [
            {
                "name": "codex",
                "adapter_version": "0.1.0",
                "cli_version": "1.2.3",
                "executable": codex_executable,
                "requested_model": "codex-model",
                "config_digest": "sha256:" + "d" * 64,
                "sandbox_policy": "workspace-write;network=false",
                "auth_mode": "chatgpt",
                "auth_provider": "openai",
                "subscription_type": None,
            },
            {
                "name": "claude",
                "adapter_version": "0.1.0",
                "cli_version": "4.5.6",
                "executable": claude_executable,
                "requested_model": "claude-model",
                "config_digest": "sha256:" + "e" * 64,
                "sandbox_policy": "safe-mode;no-shell;no-web",
                "auth_mode": "claude.ai",
                "auth_provider": "firstParty",
                "subscription_type": "pro",
            },
        ],
        "trials": [
            {
                "sequence": sequence,
                "run_id": f"portable-plan-{host}-{ordinal}",
                "host": host,
                "ordinal": ordinal,
            }
            for sequence, (host, ordinal) in enumerate(
                (
                    ("codex", 1),
                    ("claude", 1),
                    ("codex", 2),
                    ("claude", 2),
                    ("codex", 3),
                    ("claude", 3),
                ),
                start=1,
            )
        ],
        "plan_digest": "",
    }
    value["plan_digest"] = _digest(value)
    return value


def _write_plan(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.mark.parametrize("origin", ["windows", "posix"])
def test_plan_replays_foreign_absolute_paths_without_digest_change(
    tmp_path: Path, origin: str
) -> None:
    value = _plan_mapping(origin)
    path = tmp_path / f"{origin}.json"
    _write_plan(path, value)

    loaded = load_plan(path)

    assert loaded.to_mapping() == value
    assert loaded.plan_digest == value["plan_digest"]
    if origin == "windows":
        assert loaded.plan_digest == WINDOWS_REPRESENTATIVE_DIGEST


@pytest.mark.parametrize(
    ("origin", "source_root", "output_root"),
    [
        ("windows", "C:/aec", "C:/aec/reports//runs/./portable-plan"),
        ("posix", "/srv//aec", "/srv//aec/./reports/runs/portable-plan"),
    ],
)
def test_plan_preserves_noncanonical_absolute_spelling_and_digest(
    tmp_path: Path, origin: str, source_root: str, output_root: str
) -> None:
    value = _plan_mapping(origin)
    value["source_root"] = source_root
    value["output_root"] = output_root
    value["plan_digest"] = _digest(value)
    path = tmp_path / f"spelling-{origin}.json"
    _write_plan(path, value)

    loaded = load_plan(path)

    assert loaded.to_mapping() == value
    assert loaded.plan_digest == value["plan_digest"]


@pytest.mark.parametrize(
    "executable",
    ["tools/codex", r"C:tools\codex.CMD", r"\tools\codex.CMD", "", "bad\x00path"],
)
def test_plan_rejects_non_absolute_or_malformed_host_executable(
    tmp_path: Path, executable: str
) -> None:
    origin = "windows" if os.name == "nt" else "posix"
    value = _plan_mapping(origin)
    hosts = cast(list[dict[str, object]], value["hosts"])
    hosts[0]["executable"] = executable
    value["plan_digest"] = _digest(value)
    path = tmp_path / "invalid-host.json"
    _write_plan(path, value)

    with pytest.raises(ValueError):
        load_plan(path)


@pytest.mark.parametrize("origin", ["windows", "posix"])
def test_plan_rejects_foreign_output_outside_source(tmp_path: Path, origin: str) -> None:
    value = _plan_mapping(origin)
    value["output_root"] = r"D:\outside" if origin == "windows" else "/outside"
    value["plan_digest"] = _digest(value)
    path = tmp_path / f"outside-{origin}.json"
    _write_plan(path, value)

    with pytest.raises(ValueError, match="contained"):
        load_plan(path)


@pytest.mark.parametrize("origin", ["windows", "posix"])
def test_plan_normalizes_parent_segments_before_containment_check(
    tmp_path: Path, origin: str
) -> None:
    value = _plan_mapping(origin)
    value["output_root"] = r"C:\aec\..\outside" if origin == "windows" else "/srv/aec/../outside"
    value["plan_digest"] = _digest(value)
    path = tmp_path / f"traversal-{origin}.json"
    _write_plan(path, value)

    with pytest.raises(ValueError, match="contained"):
        load_plan(path)


def test_worker_rejects_foreign_or_ambiguous_executable_before_local_io(
    tmp_path: Path,
) -> None:
    local_origin = "windows" if os.name == "nt" else "posix"
    value = _plan_mapping(local_origin)
    hosts = cast(list[dict[str, object]], value["hosts"])
    hosts[0]["executable"] = "/opt/aec/bin/codex" if os.name == "nt" else "//host/share/codex"
    value["plan_digest"] = _digest(value)
    path = tmp_path / "foreign-executable.json"
    _write_plan(path, value)

    def unexpected_source_read(_: Path) -> tuple[str, tuple[str, ...]]:
        raise AssertionError("foreign executable reached local I/O")

    with pytest.raises(ValueError, match="current runtime"):
        run_experiment(
            path,
            cast(str, value["plan_digest"]),
            source_state_reader=unexpected_source_read,
        )


def test_worker_rejects_foreign_plan_before_local_io_or_host_execution(tmp_path: Path) -> None:
    foreign_origin = "posix" if os.name == "nt" else "windows"
    value = _plan_mapping(foreign_origin)
    path = tmp_path / "foreign.json"
    _write_plan(path, value)

    def unexpected_source_read(_: Path) -> tuple[str, tuple[str, ...]]:
        raise AssertionError("foreign source path reached local I/O")

    with pytest.raises(ValueError, match="current runtime"):
        run_experiment(
            path,
            cast(str, value["plan_digest"]),
            source_state_reader=unexpected_source_read,
        )
