from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from agentic_conformance.experiment_plan import (
    HostBinding,
    build_auth_plan,
    load_plan,
    write_plan,
)

REVISION = "a" * 40
SCENARIO_DIGEST = "sha256:" + "b" * 64
FIXTURE_DIGEST = "sha256:" + "c" * 64


def _host(name: str) -> HostBinding:
    return HostBinding(
        name=name,
        adapter_version="1.2.3",
        cli_version="9.8.7",
        executable=f"C:/tools/{name}.CMD",
        requested_model=f"{name}-model",
        config_digest="sha256:" + "d" * 64,
        sandbox_policy=f"{name}-restricted-workspace",
    )


def _plan(tmp_path: Path):
    return build_auth_plan(
        batch_id="m4-neutral-20260828",
        benchmark_revision=REVISION,
        source_root=tmp_path.resolve(),
        output_root=(tmp_path / "runs").resolve(),
        scenario_version="1.0.0",
        scenario_digest=SCENARIO_DIGEST,
        fixture_version="1.0.0",
        fixture_digest=FIXTURE_DIGEST,
        codex=_host("codex"),
        claude=_host("claude"),
        created_at="2026-08-28T12:00:00Z",
    )


def test_builds_exact_bound_alternating_six_trial_plan(tmp_path: Path) -> None:
    plan = _plan(tmp_path)

    assert plan.schema_version == "0.1"
    assert plan.label == "NEUTRAL_AUTONOMOUS_BASELINE"
    assert plan.benchmark_revision == REVISION
    assert plan.scenario_id == "AUTH-001"
    assert plan.scenario_version == "1.0.0"
    assert plan.scenario_digest == SCENARIO_DIGEST
    assert plan.fixture_digest == FIXTURE_DIGEST
    assert plan.observation_mode == "BLACK_BOX"
    assert plan.network_policy == "RESTRICTED"
    assert plan.retry_limit == 0
    assert [trial.host for trial in plan.trials] == [
        "codex",
        "claude",
        "codex",
        "claude",
        "codex",
        "claude",
    ]
    assert [trial.ordinal for trial in plan.trials] == [1, 1, 2, 2, 3, 3]
    assert len({trial.run_id for trial in plan.trials}) == 6
    assert plan.plan_digest.startswith("sha256:")
    assert plan.to_mapping()["plan_digest"] == plan.plan_digest


def test_plan_is_immutable_and_digest_detects_mutation(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    with pytest.raises(FrozenInstanceError):
        plan.batch_id = "changed"  # type: ignore[misc]

    value = plan.to_mapping()
    value["network_policy"] = "ALLOW"
    path = plan.output_root / "experiment-plan.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="digest"):
        load_plan(path)


def test_atomic_round_trip_and_schema_validation(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    path = plan.output_root / "experiment-plan.json"

    write_plan(path, plan)

    assert load_plan(path) == plan
    assert not path.with_suffix(".json.tmp").exists()

    value = plan.to_mapping()
    value["unexpected"] = True
    payload = {key: item for key, item in value.items() if key != "plan_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    value["plan_digest"] = "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_plan(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("retry_limit", 1, "retry"),
        ("observation_mode", "PASSIVE_INSTRUMENTED", "observation"),
        ("benchmark_revision", "not-a-sha", "revision"),
        ("source_root", Path("relative"), "absolute"),
        ("output_root", Path("relative"), "absolute"),
    ],
)
def test_rejects_invalid_semantics(tmp_path: Path, field: str, value: object, message: str) -> None:
    changed = replace(_plan(tmp_path), **{field: value}, plan_digest="")
    with pytest.raises(ValueError, match=message):
        changed.validated()


def test_rejects_trial_order_duplicate_ids_and_output_escape(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    changed_order = replace(plan, trials=tuple(reversed(plan.trials)), plan_digest="")
    with pytest.raises(ValueError, match="order"):
        changed_order.validated()

    trials = list(plan.trials)
    trials[1] = replace(trials[1], run_id=trials[0].run_id)
    duplicate = replace(plan, trials=tuple(trials), plan_digest="")
    with pytest.raises(ValueError, match="unique"):
        duplicate.validated()

    escaped = replace(plan, output_root=plan.source_root.parent / "outside", plan_digest="")
    with pytest.raises(ValueError, match="contained"):
        escaped.validated()


def test_write_requires_bound_output_location(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    with pytest.raises(ValueError, match="output root"):
        write_plan(tmp_path / "elsewhere.json", plan)
