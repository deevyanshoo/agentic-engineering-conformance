import json

import pytest

from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.result import ControlResponse, Outcome, RunClassification, RunResult
from agentic_conformance.scenario import Domain, ObservationMode, Scenario


def test_result_enums_cover_declared_semantics() -> None:
    assert {item.value for item in RunClassification} == {
        "GUARDED_PASS",
        "BEHAVIORAL_PASS",
        "FAIL",
        "INCONCLUSIVE",
        "INVALID_RUN",
        "UNSUPPORTED",
    }
    assert {item.value for item in Outcome} == {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"}
    assert {item.value for item in ControlResponse} == {
        "PREVENTED",
        "ISOLATED",
        "SERIALIZED",
        "DETECTED_AND_RECOVERED",
        "BEHAVIOR_ONLY",
        "NOT_OBSERVABLE",
    }


def test_evidence_artifact_canonicalizes_and_copies_input() -> None:
    source = {"behavior": "B", "workers": ["one", "two"]}
    artifact = EvidenceArtifact.create(
        artifact_id="final",
        level=EvidenceLevel.E1,
        kind="final_behavior",
        producer="reference",
        data=source,
        subject_digest="sha256:candidate-b",
    )
    source["behavior"] = "A"
    assert artifact.data == {"behavior": "B", "workers": ["one", "two"]}
    assert artifact.digest.startswith("sha256:")
    assert artifact.subject_digest == "sha256:candidate-b"


def test_bundle_round_trip_preserves_evidence_and_ground_truth() -> None:
    artifact = EvidenceArtifact.create(
        "final", EvidenceLevel.E1, "final_behavior", "runner", {"behavior": "B"}
    )
    bundle = EvidenceBundle.create(
        scenario_id="AUTH-001",
        scenario_version="1.0.0",
        scenario_digest="sha256:scenario",
        ground_truth={"current": "B", "stale": "A"},
        artifacts=(artifact,),
        limitations=("black-box fixture",),
    )
    restored = EvidenceBundle.from_json(bundle.to_json())
    assert restored == bundle
    assert restored.ground_truth == {"current": "B", "stale": "A"}
    assert restored.artifacts_of_kind("final_behavior") == (artifact,)


def test_e4_assertion_is_not_deterministically_admissible() -> None:
    assertion = EvidenceArtifact.create(
        "claim", EvidenceLevel.E4, "final_behavior", "agent", {"behavior": "B"}
    )
    observed = EvidenceArtifact.create(
        "tree", EvidenceLevel.E1, "final_behavior", "runner", {"behavior": "B"}
    )
    bundle = EvidenceBundle.create("AUTH-001", "1.0.0", "sha256:s", {}, (assertion, observed))
    assert bundle.admissible_artifacts("final_behavior") == (observed,)


def test_stored_artifact_rejects_payload_digest_mismatch() -> None:
    artifact = EvidenceArtifact.create(
        "final", EvidenceLevel.E1, "final_behavior", "runner", {"behavior": "B"}
    )
    stored = artifact.to_mapping()
    stored["data"] = {"behavior": "A"}
    with pytest.raises(ValueError, match="digest"):
        EvidenceArtifact.from_mapping(stored)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("id", "relabeled"),
        ("level", "E1"),
        ("kind", "final_behavior"),
        ("producer", "trusted-runner"),
        ("subject_digest", "sha256:other-subject"),
    ],
)
def test_stored_artifact_rejects_provenance_relabeling(field: str, replacement: str) -> None:
    artifact = EvidenceArtifact.create(
        "claim",
        EvidenceLevel.E4,
        "agent_assertion",
        "agent",
        {"behavior": "B"},
        "sha256:candidate-b",
    )
    stored = artifact.to_mapping()
    stored[field] = replacement
    with pytest.raises(ValueError, match="digest"):
        EvidenceArtifact.from_mapping(stored)


def test_scenario_and_result_round_trip() -> None:
    scenario = Scenario.from_mapping(
        {
            "schema_version": "0.1",
            "id": "REC-001",
            "version": "1.0.0",
            "title": "Context loss",
            "domain": "REC",
            "required_capabilities": ["durable_state.read"],
            "functional_oracle": "reconstruction.durable_state",
            "control_oracle": "reconstruction.durable_state",
            "observation_mode": "BLACK_BOX",
        }
    )
    assert scenario.domain is Domain.REC
    assert scenario.observation_mode is ObservationMode.BLACK_BOX
    assert Scenario.from_json(scenario.to_json()) == scenario

    result = RunResult(
        functional=Outcome.PASS,
        control=Outcome.PASS,
        classification=RunClassification.GUARDED_PASS,
        control_response=ControlResponse.PREVENTED,
        reasons=("protected",),
        limitations=(),
    )
    assert RunResult.from_mapping(json.loads(json.dumps(result.to_mapping()))) == result


@pytest.mark.parametrize("defect", ["future_version", "extra_field", "missing_field"])
def test_stored_bundle_rejects_incompatible_or_open_contracts(defect: str) -> None:
    bundle = EvidenceBundle.create("AUTH-001", "1.0.0", "sha256:s", {}, ())
    stored = json.loads(bundle.to_json())
    if defect == "future_version":
        stored["schema_version"] = "999"
    elif defect == "extra_field":
        stored["unexpected"] = True
    else:
        del stored["scenario_version"]
    with pytest.raises(ValueError, match="stored evidence"):
        EvidenceBundle.from_json(json.dumps(stored))


def test_stored_artifact_rejects_unknown_fields() -> None:
    artifact = EvidenceArtifact.create(
        "final", EvidenceLevel.E1, "final_behavior", "runner", {"behavior": "B"}
    )
    stored = artifact.to_mapping()
    stored["unexpected"] = True
    with pytest.raises(ValueError, match="stored evidence artifact"):
        EvidenceArtifact.from_mapping(stored)


def test_direct_artifact_constructor_rejects_forged_digest() -> None:
    with pytest.raises(ValueError, match="digest"):
        EvidenceArtifact(
            artifact_id="forged",
            level=EvidenceLevel.E1,
            kind="final_behavior",
            producer="ADAPTER_OBSERVER",
            data_json='{"behavior":"B"}',
            digest="sha256:bogus",
            subject_digest=None,
        )


def test_run_result_rejects_semantically_impossible_combination() -> None:
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        RunResult(
            functional=Outcome.PASS,
            control=Outcome.PASS,
            classification=RunClassification.UNSUPPORTED,
            control_response=ControlResponse.PREVENTED,
            reasons=("impossible",),
            limitations=(),
        )


def test_guarded_result_requires_a_functional_outcome() -> None:
    with pytest.raises(ValueError, match="GUARDED_PASS"):
        RunResult(
            functional=Outcome.NOT_RUN,
            control=Outcome.PASS,
            classification=RunClassification.GUARDED_PASS,
            control_response=ControlResponse.PREVENTED,
            reasons=("impossible",),
            limitations=(),
        )


@pytest.mark.parametrize(
    ("classification", "control", "response"),
    [
        (RunClassification.GUARDED_PASS, Outcome.PASS, ControlResponse.PREVENTED),
        (
            RunClassification.BEHAVIORAL_PASS,
            Outcome.PASS,
            ControlResponse.BEHAVIOR_ONLY,
        ),
        (RunClassification.FAIL, Outcome.FAIL, ControlResponse.NOT_OBSERVABLE),
        (
            RunClassification.INCONCLUSIVE,
            Outcome.INCONCLUSIVE,
            ControlResponse.NOT_OBSERVABLE,
        ),
    ],
)
@pytest.mark.parametrize("not_run_dimension", ["functional", "control"])
def test_executed_classification_rejects_not_run_dimension(
    classification: RunClassification,
    control: Outcome,
    response: ControlResponse,
    not_run_dimension: str,
) -> None:
    functional = (
        Outcome.INCONCLUSIVE if classification is RunClassification.INCONCLUSIVE else Outcome.PASS
    )
    with pytest.raises(ValueError, match="NOT_RUN"):
        RunResult(
            functional=Outcome.NOT_RUN if not_run_dimension == "functional" else functional,
            control=Outcome.NOT_RUN if not_run_dimension == "control" else control,
            classification=classification,
            control_response=response,
            reasons=("impossible",),
            limitations=(),
        )
