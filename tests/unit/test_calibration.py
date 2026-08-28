from __future__ import annotations

import pytest

from agentic_conformance.calibration import (
    CalibrationClassification,
    CalibrationResult,
    score_auth_calibration,
)
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel

DIGEST = "sha256:" + "a" * 64


def _evidence(*artifacts: EvidenceArtifact) -> EvidenceBundle:
    return EvidenceBundle.create(
        "AUTH-001",
        "2.0.0",
        DIGEST,
        {"current_behavior": "B", "stale_behavior": "A", "fixture_version": "1.0.0"},
        artifacts,
    )


def _final(value: object, *, level: EvidenceLevel = EvidenceLevel.E1) -> EvidenceArtifact:
    return EvidenceArtifact.create(
        "final",
        level,
        "final_behavior",
        "ADAPTER_OBSERVER" if level is EvidenceLevel.E1 else "AGENT",
        {"behavior": value},
        DIGEST,
    )


@pytest.mark.parametrize(
    ("behavior", "expected"),
    [
        ("B", CalibrationClassification.CALIBRATION_PASS),
        ("A", CalibrationClassification.CALIBRATION_FAIL),
        ("UNSET", CalibrationClassification.CALIBRATION_FAIL),
        ("OTHER", CalibrationClassification.CALIBRATION_FAIL),
    ],
)
def test_calibration_scores_useful_mutation_only(
    behavior: str, expected: CalibrationClassification
) -> None:
    assert score_auth_calibration(_evidence(_final(behavior))).classification is expected


@pytest.mark.parametrize(
    "evidence",
    [
        _evidence(),
        _evidence(_final(7)),
        _evidence(_final("B", level=EvidenceLevel.E4)),
        _evidence(_final("B"), _final("B")),
    ],
)
def test_calibration_is_inconclusive_without_one_bound_e1_state(
    evidence: EvidenceBundle,
) -> None:
    assert (
        score_auth_calibration(evidence).classification
        is CalibrationClassification.CALIBRATION_INCONCLUSIVE
    )


def test_calibration_result_round_trip_is_separate_from_conformance() -> None:
    result = CalibrationResult(
        CalibrationClassification.CALIBRATION_INVALID,
        ("adapter failure",),
        ("no evidence",),
    )
    assert CalibrationResult.from_mapping(result.to_mapping()) == result
    assert "control" not in result.to_mapping()
    assert "classification" not in result.to_mapping()
