from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_conformance.calibration import CalibrationClassification
from agentic_conformance.experiment_aggregate import (
    TrialOutcome,
    build_batch_summary,
    load_outcome,
    write_outcome,
)
from agentic_conformance.experiment_plan import (
    HostBinding,
    TrialCondition,
    TrialSpec,
    build_paired_auth_plan,
)
from agentic_conformance.result import Outcome, RunClassification


def _host(name: str) -> HostBinding:
    return HostBinding(
        name,
        "1.0",
        "2.0",
        f"C:/tools/{name}.CMD",
        f"{name}-model",
        "sha256:" + "a" * 64,
        "restricted",
        "chatgpt" if name == "codex" else "claude.ai",
        "openai" if name == "codex" else "firstParty",
        None if name == "codex" else "pro",
    )


def _plan(tmp_path: Path):
    return build_paired_auth_plan(
        batch_id="m5-paired-test",
        benchmark_revision="b" * 40,
        source_root=tmp_path.resolve(),
        output_root=(tmp_path / "runs").resolve(),
        scenario_version="2.0.0",
        scenario_digest="sha256:" + "c" * 64,
        fixture_version="1.0.0",
        fixture_base_digest="sha256:" + "d" * 64,
        calibration_prompt_digest="sha256:" + "e" * 64,
        auth_conflict_prompt_digest="sha256:" + "f" * 64,
        codex=_host("codex"),
        claude=_host("claude"),
        created_at="2026-08-29T12:00:00Z",
    )


def _calibration(trial: TrialSpec, passed: bool) -> TrialOutcome:
    return TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=True,
        classification=None,
        functional=Outcome.PASS if passed else Outcome.FAIL,
        control=Outcome.NOT_RUN,
        limitations=(),
        cli_version="2.0",
        requested_model=f"{trial.host}-model",
        observed_model_identifier=None,
        config_digest="sha256:" + "a" * 64,
        evidence_digest="sha256:" + "1" * 64,
        manifest_digest="sha256:" + "2" * 64,
        rescored_equal=True,
        process_returncode=0,
        condition=TrialCondition.CALIBRATION,
        calibration_classification=(
            CalibrationClassification.CALIBRATION_PASS
            if passed
            else CalibrationClassification.CALIBRATION_FAIL
        ),
    )


def _auth(trial: TrialSpec) -> TrialOutcome:
    return TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=True,
        classification=RunClassification.INCONCLUSIVE,
        functional=Outcome.FAIL,
        control=Outcome.INCONCLUSIVE,
        limitations=(),
        cli_version="2.0",
        requested_model=f"{trial.host}-model",
        observed_model_identifier=None,
        config_digest="sha256:" + "a" * 64,
        evidence_digest="sha256:" + "1" * 64,
        manifest_digest="sha256:" + "2" * 64,
        rescored_equal=True,
        process_returncode=0,
        condition=TrialCondition.AUTH_CONFLICT,
    )


def test_paired_outcome_round_trip_keeps_calibration_separate(tmp_path: Path) -> None:
    trial = _plan(tmp_path).trials[0]
    outcome = _calibration(trial, True)
    path = tmp_path / "outcome.json"
    write_outcome(path, outcome)
    assert load_outcome(path) == outcome
    value = outcome.to_mapping()
    assert value["schema_version"] == "0.2"
    assert value["calibration_outcome"] == "CALIBRATION_PASS"
    assert value["classification"] is None
    assert value["control"] == "NOT_RUN"


def test_paired_aggregate_reports_interpretability_without_ranking(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    outcomes = tuple(
        _calibration(trial, passed=trial.host == "codex")
        if trial.condition is TrialCondition.CALIBRATION
        else _auth(trial)
        for trial in plan.trials
    )

    summary = build_batch_summary(plan, outcomes)

    assert summary["scheduled_total"] == 12
    assert summary["hosts"]["codex"]["interpretability_cases"] == {"CASE_3": 3}
    assert summary["hosts"]["claude"]["interpretability_cases"] == {"CASE_4": 3}
    serialized = json.dumps(summary).casefold()
    for forbidden in ("winner", "ranking", "beats", "better"):
        assert forbidden not in serialized


def test_calibration_outcome_rejects_conformance_classification(tmp_path: Path) -> None:
    trial = _plan(tmp_path).trials[0]
    with pytest.raises(ValueError, match="calibration"):
        replace(
            _calibration(trial, True),
            classification=RunClassification.BEHAVIORAL_PASS,
            outcome_digest="",
        ).validated()


def test_paired_aggregate_rejects_same_host_config_drift(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    outcomes = tuple(
        _calibration(trial, True) if trial.condition is TrialCondition.CALIBRATION else _auth(trial)
        for trial in plan.trials
    )
    changed = list(outcomes)
    changed[1] = replace(
        changed[1], config_digest="sha256:" + "9" * 64, outcome_digest=""
    ).validated()
    with pytest.raises(ValueError, match="configuration"):
        build_batch_summary(plan, tuple(changed))
