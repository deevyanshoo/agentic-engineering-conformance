from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_conformance.experiment_aggregate import (
    TrialOutcome,
    build_batch_summary,
    load_outcome,
    write_outcome,
)
from agentic_conformance.experiment_plan import HostBinding, build_auth_plan
from agentic_conformance.result import Outcome, RunClassification


def _host(name: str) -> HostBinding:
    return HostBinding(
        name,
        "1.0.0",
        "2.0.0",
        f"C:/tools/{name}.CMD",
        f"{name}-model",
        "sha256:" + ("c" if name == "codex" else "d") * 64,
        f"{name}-sandbox",
    )


def _plan(tmp_path: Path):
    return build_auth_plan(
        batch_id="m4-neutral-aggregate",
        benchmark_revision="a" * 40,
        source_root=tmp_path.resolve(),
        output_root=(tmp_path / "runs").resolve(),
        scenario_version="1.0.0",
        scenario_digest="sha256:" + "b" * 64,
        fixture_version="1.0.0",
        fixture_digest="sha256:" + "e" * 64,
        codex=_host("codex"),
        claude=_host("claude"),
        created_at="2026-08-28T12:00:00Z",
    )


def _outcome(
    trial,
    classification: RunClassification,
    functional: Outcome,
    control: Outcome,
    *,
    attempted: bool = True,
) -> TrialOutcome:
    return TrialOutcome.create(
        sequence=trial.sequence,
        run_id=trial.run_id,
        host=trial.host,
        ordinal=trial.ordinal,
        attempted=attempted,
        classification=classification,
        functional=functional,
        control=control,
        limitations=(f"{trial.host}-limitation",),
        cli_version="2.0.0",
        model_identifier=f"{trial.host}-observed",
        config_digest="sha256:" + ("c" if trial.host == "codex" else "d") * 64,
        evidence_digest="sha256:" + "f" * 64 if attempted else None,
        manifest_digest="sha256:" + "1" * 64 if attempted else None,
        rescored_equal=True if attempted else None,
        process_returncode=0 if attempted else None,
    )


def test_atomic_outcome_round_trip_detects_mutation(tmp_path: Path) -> None:
    trial = _plan(tmp_path).trials[0]
    outcome = _outcome(trial, RunClassification.BEHAVIORAL_PASS, Outcome.PASS, Outcome.PASS)
    path = tmp_path / "outcome.json"

    write_outcome(path, outcome)
    assert load_outcome(path) == outcome

    value = json.loads(path.read_text(encoding="utf-8"))
    value["classification"] = "FAIL"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        load_outcome(path)


def test_aggregate_counts_all_result_classes_without_ranking(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    cases = (
        (RunClassification.GUARDED_PASS, Outcome.PASS, Outcome.PASS, True),
        (RunClassification.BEHAVIORAL_PASS, Outcome.PASS, Outcome.PASS, True),
        (RunClassification.FAIL, Outcome.PASS, Outcome.FAIL, True),
        (RunClassification.INCONCLUSIVE, Outcome.INCONCLUSIVE, Outcome.PASS, True),
        (RunClassification.UNSUPPORTED, Outcome.NOT_RUN, Outcome.NOT_RUN, False),
        (RunClassification.INVALID_RUN, Outcome.NOT_RUN, Outcome.NOT_RUN, True),
    )
    outcomes = tuple(
        _outcome(trial, classification, functional, control, attempted=attempted)
        for trial, (classification, functional, control, attempted) in zip(
            plan.trials, cases, strict=True
        )
    )

    summary = build_batch_summary(plan, outcomes)

    assert summary["scheduled_total"] == 6
    assert summary["recorded_total"] == 6
    codex = summary["hosts"]["codex"]
    claude = summary["hosts"]["claude"]
    assert codex["scheduled_count"] == 3
    assert codex["executed_count"] == 2
    assert codex["classifications"] == {
        "GUARDED_PASS": 1,
        "BEHAVIORAL_PASS": 0,
        "FAIL": 1,
        "INCONCLUSIVE": 0,
        "INVALID_RUN": 0,
        "UNSUPPORTED": 1,
    }
    assert codex["functional"] == {"PASS": 2, "FAIL": 0}
    assert codex["control"] == {"PASS": 1, "FAIL": 1}
    assert claude["executed_count"] == 3
    assert claude["classifications"]["BEHAVIORAL_PASS"] == 1
    assert claude["classifications"]["INCONCLUSIVE"] == 1
    assert claude["classifications"]["INVALID_RUN"] == 1
    assert claude["functional"] == {"PASS": 1, "FAIL": 0}
    assert claude["control"] == {"PASS": 2, "FAIL": 0}
    assert not {"winner", "ranking", "composite", "superiority"} & summary.keys()
    assert not {"winner", "ranking", "composite", "superiority"} & codex.keys()


def test_aggregate_rejects_missing_reordered_or_mismatched_trials(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    outcomes = tuple(
        _outcome(trial, RunClassification.BEHAVIORAL_PASS, Outcome.PASS, Outcome.PASS)
        for trial in plan.trials
    )
    with pytest.raises(ValueError, match="exactly six"):
        build_batch_summary(plan, outcomes[:-1])
    with pytest.raises(ValueError, match="order"):
        build_batch_summary(plan, tuple(reversed(outcomes)))
