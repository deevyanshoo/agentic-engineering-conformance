import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle
from agentic_conformance.oracle import OracleRegistry
from agentic_conformance.result import Outcome, RunClassification
from agentic_conformance.runner import Runner, rescore, scenario_digest
from agentic_conformance.scenario import Scenario, load_scenario
from agentic_conformance.seed_oracles import reconstruct_durable_state, seed_oracle_registry

ROOT = Path(__file__).parents[2]
SCENARIOS = (
    "scenarios/authority/AUTH-001/scenario.json",
    "scenarios/mutation/MUT-001/scenario.json",
    "scenarios/completion/COMP-002/scenario.json",
    "scenarios/review/REV-002/scenario.json",
    "scenarios/invalidation/INV-003/scenario.json",
    "scenarios/reconstruction/REC-001/scenario.json",
)


def load_schema() -> dict[str, Any]:
    with (ROOT / "schemas/scenario.schema.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def scenario(scenario_id: str) -> Scenario:
    path = next(path for path in SCENARIOS if scenario_id in path)
    return load_scenario(ROOT / path, ROOT / "schemas/scenario.schema.json")


def run_mode(scenario_id: str, mode: str, registry: OracleRegistry | None = None):
    return Runner(registry or seed_oracle_registry()).run(
        scenario(scenario_id), ReferenceAdapter(mode=mode)
    )


def test_exactly_six_seed_scenarios_validate_and_bind_fixtures() -> None:
    discovered = sorted(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "scenarios").glob("*/*/scenario.json")
    )
    assert discovered == sorted(SCENARIOS)
    validator = Draft202012Validator(load_schema())
    for relative_path in SCENARIOS:
        with (ROOT / relative_path).open(encoding="utf-8") as handle:
            definition = json.load(handle)
        validator.validate(definition)
        fixture_path = ROOT / definition["fixture"]["path"]
        digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        assert definition["fixture"]["digest"] == f"sha256:{digest}"


@pytest.mark.parametrize("scenario_id", ["AUTH-001", "MUT-001"])
def test_behavioral_success_preserves_invariant_without_control_exercise(scenario_id: str) -> None:
    result = run_mode(scenario_id, "behavioral_pass").result
    assert result.functional is Outcome.PASS
    assert result.control is Outcome.PASS
    assert result.classification is RunClassification.BEHAVIORAL_PASS


def test_stale_context_cannot_override_current_authority() -> None:
    assert (
        run_mode("AUTH-001", "guarded_pass").result.classification is RunClassification.GUARDED_PASS
    )
    violation = run_mode("AUTH-001", "control_violation").result
    assert (violation.functional, violation.control) == (Outcome.FAIL, Outcome.FAIL)


def test_overlapping_writers_reject_silent_lost_update() -> None:
    guarded = run_mode("MUT-001", "guarded_pass").result
    assert (guarded.functional, guarded.control) == (Outcome.PASS, Outcome.PASS)
    violation = run_mode("MUT-001", "control_violation").result
    assert (violation.functional, violation.control) == (Outcome.FAIL, Outcome.FAIL)


def test_stale_verification_cannot_admit_changed_source() -> None:
    violation = run_mode("COMP-002", "control_violation").result
    assert violation.functional is Outcome.PASS
    assert violation.control is Outcome.FAIL
    assert violation.classification is RunClassification.FAIL


def test_stale_review_cannot_admit_changed_candidate() -> None:
    violation = run_mode("REV-002", "control_violation").result
    assert violation.functional is Outcome.PASS
    assert violation.control is Outcome.FAIL


def test_completion_rejects_payloads_with_wrong_artifact_subject_binding() -> None:
    current = scenario("COMP-002")
    record = Runner(seed_oracle_registry()).run(current, ReferenceAdapter(mode="guarded_pass"))
    assert record.evidence is not None
    rebound = tuple(
        EvidenceArtifact.create(
            artifact.artifact_id,
            artifact.level,
            artifact.kind,
            artifact.producer,
            artifact.data,
            "sha256:wrong-subject",
        )
        if artifact.kind in {"candidate_state", "verifier_record", "completion_state"}
        else artifact
        for artifact in record.evidence.artifacts
    )
    evidence = EvidenceBundle.create(
        current.scenario_id,
        current.version,
        scenario_digest(current),
        current.ground_truth,
        rebound,
    )
    assert rescore(current, evidence, seed_oracle_registry()).control is Outcome.FAIL


def test_current_review_must_be_independent() -> None:
    current = scenario("REV-002")
    record = Runner(seed_oracle_registry()).run(current, ReferenceAdapter(mode="guarded_pass"))
    assert record.evidence is not None
    candidate = current.ground_truth["candidate_b_digest"]
    replaced: list[EvidenceArtifact] = []
    for artifact in record.evidence.artifacts:
        if artifact.kind == "review_record":
            replaced.append(
                EvidenceArtifact.create(
                    "review-b",
                    artifact.level,
                    artifact.kind,
                    artifact.producer,
                    {"subject_digest": candidate, "approved": True, "independent": False},
                    candidate,
                )
            )
        elif artifact.kind == "review_state":
            replaced.append(
                EvidenceArtifact.create(
                    artifact.artifact_id,
                    artifact.level,
                    artifact.kind,
                    artifact.producer,
                    {"review_satisfied": True, "subject_digest": candidate},
                    candidate,
                )
            )
        else:
            replaced.append(artifact)
    evidence = EvidenceBundle.create(
        current.scenario_id,
        current.version,
        scenario_digest(current),
        current.ground_truth,
        replaced,
    )
    assert rescore(current, evidence, seed_oracle_registry()).control is Outcome.FAIL


@pytest.mark.parametrize("mode", ["under_invalidation", "over_invalidation"])
def test_selective_invalidation_rejects_under_and_over_invalidation(mode: str) -> None:
    result = run_mode("INV-003", mode).result
    assert result.functional is Outcome.PASS
    assert result.control is Outcome.FAIL


def test_selective_invalidation_preserves_unaffected_sibling() -> None:
    result = run_mode("INV-003", "guarded_pass").result
    assert result.classification is RunClassification.GUARDED_PASS


@pytest.mark.parametrize("mode", ["missing_state", "inconsistent_state"])
def test_reconstruction_does_not_fabricate_missing_or_inconsistent_state(mode: str) -> None:
    result = run_mode("REC-001", mode).result
    assert result.classification in {RunClassification.INCONCLUSIVE, RunClassification.FAIL}
    assert result.control is not Outcome.PASS


def test_reconstruction_matches_durable_ground_truth() -> None:
    result = run_mode("REC-001", "guarded_pass").result
    assert (result.functional, result.control) == (Outcome.PASS, Outcome.PASS)


def test_reconstruction_interpreter_matches_hand_authored_fixture_ground_truth() -> None:
    current = scenario("REC-001")
    assert (
        reconstruct_durable_state(current.ground_truth["durable_state"])
        == current.ground_truth["expected_reconstruction"]
    )


def test_consistently_fabricated_durable_state_and_reconstruction_fail() -> None:
    current = scenario("REC-001")
    record = Runner(seed_oracle_registry()).run(current, ReferenceAdapter(mode="guarded_pass"))
    assert record.evidence is not None
    fabricated_durable = {
        "objective": "Invented objective",
        "candidate_digest": "sha256:invented",
        "nodes": {"X": {"status": "COMPLETE", "dependencies": []}},
        "evidence": [],
    }
    fabricated_reconstruction = {
        "objective": "Invented objective",
        "completed_nodes": ["X"],
        "runnable_nodes": [],
        "blocked_nodes": [],
        "stale_evidence": [],
        "pending_review": [],
        "pending_publication": [],
    }
    artifacts = tuple(
        EvidenceArtifact.create(
            artifact.artifact_id,
            artifact.level,
            artifact.kind,
            artifact.producer,
            fabricated_durable
            if artifact.kind == "durable_state"
            else fabricated_reconstruction
            if artifact.kind == "reconstruction"
            else artifact.data,
            artifact.subject_digest,
        )
        if artifact.kind in {"durable_state", "reconstruction"}
        else artifact
        for artifact in record.evidence.artifacts
    )
    fabricated = EvidenceBundle.create(
        current.scenario_id,
        current.version,
        scenario_digest(current),
        current.ground_truth,
        artifacts,
    )
    result = rescore(current, fabricated, seed_oracle_registry())
    assert result.functional is Outcome.FAIL
    assert result.control is Outcome.FAIL
