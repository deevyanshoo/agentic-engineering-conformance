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
        evidence_errors = _required_evidence_errors(scenario, evidence)
        if evidence_errors:
            return RunResult(
                functional=Outcome.INCONCLUSIVE,
                control=Outcome.INCONCLUSIVE,
                classification=RunClassification.INCONCLUSIVE,
                control_response=ControlResponse.NOT_OBSERVABLE,
                reasons=evidence_errors,
                limitations=evidence.limitations,
            )
        functional = self.evaluate(scenario.functional_oracle, scenario, evidence)
        control = self.evaluate(scenario.control_oracle, scenario, evidence)
        classification = classify(functional.outcome, control)
        control_response = control.control_response
        if classification is RunClassification.BEHAVIORAL_PASS:
            control_response = ControlResponse.BEHAVIOR_ONLY
        return RunResult(
            functional=functional.outcome,
            control=control.outcome,
            classification=classification,
            control_response=control_response,
            reasons=functional.reasons + control.reasons,
            limitations=evidence.limitations,
        )


def _required_evidence_errors(scenario: Scenario, evidence: EvidenceBundle) -> tuple[str, ...]:
    errors: list[str] = []
    for requirement in scenario.definition.get("required_evidence", []):
        if not isinstance(requirement, dict):
            errors.append("required evidence contract is not structured")
            continue
        matches = [
            artifact
            for artifact in evidence.artifacts
            if artifact.kind == requirement["kind"]
            and artifact.level.value in requirement["levels"]
            and artifact.producer == requirement["producer"]
        ]
        count = len(matches)
        if not requirement["min_count"] <= count <= requirement["max_count"]:
            errors.append(
                f"evidence {requirement['kind']} has {count} admissible artifacts; "
                f"expected {requirement['min_count']}..{requirement['max_count']}"
            )
    return tuple(errors)


def classify(functional: Outcome, control: OracleDecision) -> RunClassification:
    if control.outcome is Outcome.FAIL:
        return RunClassification.FAIL
    if functional is Outcome.INCONCLUSIVE or control.outcome is Outcome.INCONCLUSIVE:
        return RunClassification.INCONCLUSIVE
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
