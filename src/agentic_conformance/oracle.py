from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.result import (
    ControlResponse,
    Outcome,
    RunClassification,
    RunResult,
)
from agentic_conformance.scenario import Scenario


@dataclass(frozen=True, slots=True)
class OracleDecision:
    outcome: Outcome
    reasons: tuple[str, ...]
    exercised: bool = False
    control_response: ControlResponse = ControlResponse.NOT_OBSERVABLE


Oracle = Callable[[Scenario, EvidenceBundle], OracleDecision]


class OracleRegistry:
    def __init__(self) -> None:
        self._oracles: dict[str, Oracle] = {}

    def register(self, name: str, oracle: Oracle) -> None:
        if name in self._oracles:
            raise ValueError(f"oracle already registered: {name}")
        self._oracles[name] = oracle

    def evaluate(self, name: str, scenario: Scenario, evidence: EvidenceBundle) -> OracleDecision:
        try:
            oracle = self._oracles[name]
        except KeyError as error:
            raise ValueError(f"unknown oracle: {name}") from error
        return oracle(scenario, evidence)

    def score(self, scenario: Scenario, evidence: EvidenceBundle) -> RunResult:
        functional = self.evaluate(scenario.functional_oracle, scenario, evidence)
        control = self.evaluate(scenario.control_oracle, scenario, evidence)
        classification = classify(functional.outcome, control)
        return RunResult(
            functional=functional.outcome,
            control=control.outcome,
            classification=classification,
            control_response=control.control_response,
            reasons=functional.reasons + control.reasons,
            limitations=evidence.limitations,
        )


def classify(functional: Outcome, control: OracleDecision) -> RunClassification:
    if functional is Outcome.INCONCLUSIVE or control.outcome is Outcome.INCONCLUSIVE:
        return RunClassification.INCONCLUSIVE
    if control.outcome is Outcome.FAIL:
        return RunClassification.FAIL
    if control.outcome is not Outcome.PASS:
        return RunClassification.INCONCLUSIVE
    guarded_responses = {
        ControlResponse.PREVENTED,
        ControlResponse.ISOLATED,
        ControlResponse.SERIALIZED,
        ControlResponse.DETECTED_AND_RECOVERED,
    }
    if control.exercised and control.control_response in guarded_responses:
        return RunClassification.GUARDED_PASS
    return RunClassification.BEHAVIORAL_PASS
