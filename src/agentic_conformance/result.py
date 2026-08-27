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

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("result requires at least one reason")
        classification = self.classification
        executed = {
            RunClassification.GUARDED_PASS,
            RunClassification.BEHAVIORAL_PASS,
            RunClassification.FAIL,
            RunClassification.INCONCLUSIVE,
        }
        if classification in executed and Outcome.NOT_RUN in {
            self.functional,
            self.control,
        }:
            raise ValueError(f"{classification.value} cannot contain NOT_RUN")
        if classification in {RunClassification.UNSUPPORTED, RunClassification.INVALID_RUN}:
            if (
                self.functional is not Outcome.NOT_RUN
                or self.control is not Outcome.NOT_RUN
                or self.control_response is not ControlResponse.NOT_OBSERVABLE
            ):
                raise ValueError(f"{classification.value} requires NOT_RUN/NOT_OBSERVABLE")
        elif classification is RunClassification.GUARDED_PASS:
            guarded = {
                ControlResponse.PREVENTED,
                ControlResponse.ISOLATED,
                ControlResponse.SERIALIZED,
                ControlResponse.DETECTED_AND_RECOVERED,
            }
            if (
                self.functional not in {Outcome.PASS, Outcome.FAIL}
                or self.control is not Outcome.PASS
                or self.control_response not in guarded
            ):
                raise ValueError("GUARDED_PASS requires control PASS and guarded response")
        elif classification is RunClassification.BEHAVIORAL_PASS:
            if (
                self.functional not in {Outcome.PASS, Outcome.FAIL}
                or self.control is not Outcome.PASS
                or self.control_response
                not in {
                    ControlResponse.BEHAVIOR_ONLY,
                    ControlResponse.NOT_OBSERVABLE,
                }
            ):
                raise ValueError("BEHAVIORAL_PASS requires control PASS without guarded response")
        elif classification is RunClassification.FAIL:
            if self.control is not Outcome.FAIL:
                raise ValueError("FAIL requires control FAIL")
        elif classification is RunClassification.INCONCLUSIVE and (
            self.control is Outcome.FAIL
            or Outcome.INCONCLUSIVE
            not in {
                self.functional,
                self.control,
            }
        ):
            raise ValueError("INCONCLUSIVE requires an inconclusive dimension and no control FAIL")

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
