from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class RunClassification(StrEnum):
    GUARDED_PASS = "GUARDED_PASS"
    BEHAVIORAL_PASS = "BEHAVIORAL_PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID_RUN = "INVALID_RUN"
    UNSUPPORTED = "UNSUPPORTED"


class ControlResponse(StrEnum):
    PREVENTED = "PREVENTED"
    ISOLATED = "ISOLATED"
    SERIALIZED = "SERIALIZED"
    DETECTED_AND_RECOVERED = "DETECTED_AND_RECOVERED"
    BEHAVIOR_ONLY = "BEHAVIOR_ONLY"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"


@dataclass(frozen=True, slots=True)
class RunResult:
    functional: Outcome
    control: Outcome
    classification: RunClassification
    control_response: ControlResponse
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "0.1",
            "functional": self.functional.value,
            "control": self.control.value,
            "classification": self.classification.value,
            "control_response": self.control_response.value,
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RunResult:
        return cls(
            functional=Outcome(value["functional"]),
            control=Outcome(value["control"]),
            classification=RunClassification(value["classification"]),
            control_response=ControlResponse(value["control_response"]),
            reasons=tuple(value["reasons"]),
            limitations=tuple(value["limitations"]),
        )
