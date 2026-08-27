import json

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
