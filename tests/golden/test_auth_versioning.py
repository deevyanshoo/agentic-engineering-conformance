from __future__ import annotations

from pathlib import Path

import pytest

from agentic_conformance.adapters.auth_fixture import validate_auth_scenario
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.result import ControlResponse, Outcome, RunClassification
from agentic_conformance.runner import rescore, scenario_digest
from agentic_conformance.scenario import Scenario, load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]
SCHEMA = ROOT / "schemas/scenario.schema.json"
V1_PATH = ROOT / "scenarios/authority/AUTH-001/scenario.json"
V2_PATH = ROOT / "scenarios/authority/AUTH-001/scenario-v2.json"
V1_DIGEST = "sha256:670a861baf9d876f89654912b762cd2fb5e42171a59fbf8d21b4e6df09fe61d7"


def _load(path: Path) -> Scenario:
    return load_scenario(path, SCHEMA)


def _score(scenario: Scenario, behavior: object | None, *, include: bool = True):
    artifacts = ()
    if include:
        artifacts = (
            EvidenceArtifact.create(
                "final",
                EvidenceLevel.E1,
                "final_behavior",
                "ADAPTER_OBSERVER",
                {"behavior": behavior},
            ),
        )
    evidence = EvidenceBundle.create(
        scenario.scenario_id,
        scenario.version,
        scenario_digest(scenario),
        scenario.ground_truth,
        artifacts,
    )
    return rescore(scenario, evidence, seed_oracle_registry())


def test_auth_v1_binding_and_historical_unset_score_are_unchanged() -> None:
    scenario = _load(V1_PATH)
    assert scenario.version == "1.0.0"
    assert scenario_digest(scenario) == V1_DIGEST

    result = _score(scenario, "UNSET")

    assert (result.functional, result.control, result.classification) == (
        Outcome.FAIL,
        Outcome.FAIL,
        RunClassification.FAIL,
    )


@pytest.mark.parametrize(
    ("behavior", "functional", "control", "classification", "response"),
    [
        (
            "B",
            Outcome.PASS,
            Outcome.PASS,
            RunClassification.BEHAVIORAL_PASS,
            ControlResponse.BEHAVIOR_ONLY,
        ),
        (
            "A",
            Outcome.FAIL,
            Outcome.FAIL,
            RunClassification.FAIL,
            ControlResponse.BEHAVIOR_ONLY,
        ),
        (
            "UNSET",
            Outcome.FAIL,
            Outcome.INCONCLUSIVE,
            RunClassification.INCONCLUSIVE,
            ControlResponse.NOT_OBSERVABLE,
        ),
        (
            "OTHER",
            Outcome.FAIL,
            Outcome.INCONCLUSIVE,
            RunClassification.INCONCLUSIVE,
            ControlResponse.NOT_OBSERVABLE,
        ),
        (
            7,
            Outcome.FAIL,
            Outcome.INCONCLUSIVE,
            RunClassification.INCONCLUSIVE,
            ControlResponse.NOT_OBSERVABLE,
        ),
    ],
)
def test_auth_v2_distinguishes_current_stale_and_no_decision(
    behavior: object,
    functional: Outcome,
    control: Outcome,
    classification: RunClassification,
    response: ControlResponse,
) -> None:
    result = _score(_load(V2_PATH), behavior)

    assert (result.functional, result.control, result.classification) == (
        functional,
        control,
        classification,
    )
    assert result.control_response is response


def test_auth_v2_missing_final_e1_is_inconclusive_in_both_dimensions() -> None:
    result = _score(_load(V2_PATH), None, include=False)

    assert (result.functional, result.control, result.classification) == (
        Outcome.INCONCLUSIVE,
        Outcome.INCONCLUSIVE,
        RunClassification.INCONCLUSIVE,
    )
    assert result.control_response is ControlResponse.NOT_OBSERVABLE


def test_real_fixture_binding_accepts_both_exact_scenario_versions() -> None:
    validate_auth_scenario(_load(V1_PATH))
    validate_auth_scenario(_load(V2_PATH))
