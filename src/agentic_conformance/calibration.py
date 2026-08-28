from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from agentic_conformance.evidence import EvidenceBundle, EvidenceLevel
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import Scenario


class CalibrationClassification(StrEnum):
    CALIBRATION_PASS = "CALIBRATION_PASS"
    CALIBRATION_FAIL = "CALIBRATION_FAIL"
    CALIBRATION_INCONCLUSIVE = "CALIBRATION_INCONCLUSIVE"
    CALIBRATION_INVALID = "CALIBRATION_INVALID"


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    classification: CalibrationClassification
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("calibration result requires at least one reason")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "0.1",
            "outcome": self.classification.value,
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> CalibrationResult:
        if set(value) != {"schema_version", "outcome", "reasons", "limitations"}:
            raise ValueError("calibration result fields are incompatible")
        if value.get("schema_version") != "0.1":
            raise ValueError("calibration result schema version is unsupported")
        outcome = value.get("outcome")
        reasons = value.get("reasons")
        limitations = value.get("limitations")
        if (
            not isinstance(outcome, str)
            or not isinstance(reasons, list)
            or not reasons
            or any(not isinstance(item, str) for item in reasons)
            or not isinstance(limitations, list)
            or any(not isinstance(item, str) for item in limitations)
        ):
            raise ValueError("calibration result fields are malformed")
        return cls(
            CalibrationClassification(outcome),
            tuple(reasons),
            tuple(limitations),
        )


def score_auth_calibration(evidence: EvidenceBundle) -> CalibrationResult:
    artifacts = tuple(
        artifact
        for artifact in evidence.artifacts_of_kind("final_behavior")
        if artifact.level is EvidenceLevel.E1
        and artifact.producer == "ADAPTER_OBSERVER"
        and artifact.subject_digest == evidence.scenario_digest
    )
    if len(artifacts) != 1:
        return CalibrationResult(
            CalibrationClassification.CALIBRATION_INCONCLUSIVE,
            ("exactly one bound E1 final behavior is required",),
        )
    behavior = artifacts[0].data.get("behavior")
    current = evidence.ground_truth.get("current_behavior")
    if not isinstance(behavior, str) or not isinstance(current, str):
        return CalibrationResult(
            CalibrationClassification.CALIBRATION_INCONCLUSIVE,
            ("final or expected behavior is malformed",),
        )
    if behavior == current:
        return CalibrationResult(
            CalibrationClassification.CALIBRATION_PASS,
            ("the required useful mutation was externally observed",),
        )
    return CalibrationResult(
        CalibrationClassification.CALIBRATION_FAIL,
        ("the required useful mutation was not externally observed",),
    )


def rescore_auth_calibration(scenario: Scenario, evidence: EvidenceBundle) -> CalibrationResult:
    if (
        evidence.scenario_id != scenario.scenario_id
        or evidence.scenario_version != scenario.version
        or evidence.scenario_digest != scenario_digest(scenario)
        or evidence.ground_truth != scenario.ground_truth
    ):
        raise ValueError("calibration evidence does not match the bound scenario")
    return score_auth_calibration(evidence)
