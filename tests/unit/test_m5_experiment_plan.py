from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.experiment_plan import (
    HostBinding,
    TrialCondition,
    build_paired_auth_plan,
    load_plan,
    write_plan,
)

REVISION = "a" * 40
DIGEST = "sha256:" + "b" * 64


def _host(name: str) -> HostBinding:
    return HostBinding(
        name=name,
        adapter_version="1.2.3",
        cli_version="9.8.7",
        executable=f"C:/tools/{name}.CMD",
        requested_model=f"{name}-model",
        config_digest="sha256:" + "c" * 64,
        sandbox_policy=f"{name}-restricted-workspace",
        auth_mode="chatgpt" if name == "codex" else "claude.ai",
        auth_provider="openai" if name == "codex" else "firstParty",
        subscription_type=None if name == "codex" else "pro",
    )


def _plan(tmp_path: Path):
    return build_paired_auth_plan(
        batch_id="m5-auth-calibration-20260829",
        benchmark_revision=REVISION,
        source_root=tmp_path.resolve(),
        output_root=(tmp_path / "runs").resolve(),
        scenario_version="2.0.0",
        scenario_digest=DIGEST,
        fixture_version="1.0.0",
        fixture_base_digest="sha256:" + "d" * 64,
        calibration_prompt_digest="sha256:" + "e" * 64,
        auth_conflict_prompt_digest="sha256:" + "f" * 64,
        codex=_host("codex"),
        claude=_host("claude"),
        created_at="2026-08-29T12:00:00Z",
    )


def test_builds_exact_twelve_slot_paired_plan(tmp_path: Path) -> None:
    plan = _plan(tmp_path)

    assert plan.schema_version == "0.2"
    assert plan.label == "AUTH_CONSTRUCT_VALIDITY_PAIRED"
    assert len(plan.trials) == 12
    assert [(trial.host, trial.condition, trial.ordinal) for trial in plan.trials] == [
        ("codex", TrialCondition.CALIBRATION, 1),
        ("codex", TrialCondition.AUTH_CONFLICT, 1),
        ("claude", TrialCondition.CALIBRATION, 1),
        ("claude", TrialCondition.AUTH_CONFLICT, 1),
        ("codex", TrialCondition.CALIBRATION, 2),
        ("codex", TrialCondition.AUTH_CONFLICT, 2),
        ("claude", TrialCondition.CALIBRATION, 2),
        ("claude", TrialCondition.AUTH_CONFLICT, 2),
        ("codex", TrialCondition.CALIBRATION, 3),
        ("codex", TrialCondition.AUTH_CONFLICT, 3),
        ("claude", TrialCondition.CALIBRATION, 3),
        ("claude", TrialCondition.AUTH_CONFLICT, 3),
    ]
    assert plan.fixture_digest == "sha256:" + "d" * 64
    assert plan.calibration_prompt_digest == "sha256:" + "e" * 64
    assert plan.auth_conflict_prompt_digest == "sha256:" + "f" * 64
    assert len({trial.run_id for trial in plan.trials}) == 12


def test_paired_plan_round_trips_and_is_digest_bound(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    path = plan.output_root / "experiment-plan.json"
    write_plan(path, plan)
    assert load_plan(path) == plan

    changed = replace(plan, calibration_prompt_digest="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="digest"):
        changed.validated()


def test_paired_plan_rejects_order_or_non_v2_scenario(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    with pytest.raises(ValueError, match="version"):
        replace(plan, scenario_version="1.0.0", plan_digest="").validated()
    with pytest.raises(ValueError, match="order"):
        replace(plan, trials=tuple(reversed(plan.trials)), plan_digest="").validated()
