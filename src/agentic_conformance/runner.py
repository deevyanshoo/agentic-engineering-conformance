from __future__ import annotations

import hashlib
from dataclasses import dataclass

from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.oracle import OracleRegistry
from agentic_conformance.result import (
    ControlResponse,
    Outcome,
    RunClassification,
    RunResult,
)
from agentic_conformance.scenario import Scenario


def scenario_digest(scenario: Scenario) -> str:
    digest = hashlib.sha256(scenario.definition_json.encode()).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True, slots=True)
class RunRecord:
    result: RunResult
    evidence: EvidenceBundle | None
    executed: bool
    missing_capabilities: tuple[str, ...] = ()
    adapter_error: str | None = None
    cleanup_error: str | None = None


class Runner:
    def __init__(self, oracles: OracleRegistry) -> None:
        self._oracles = oracles

    def run(self, scenario: Scenario, adapter: Adapter) -> RunRecord:
        try:
            capabilities = adapter.probe()
        except Exception as error:
            return RunRecord(_invalid_result(error), None, False, adapter_error=_error_text(error))

        missing = tuple(sorted(scenario.required_capabilities - capabilities))
        if missing:
            return RunRecord(
                _unsupported_result(missing), None, False, missing_capabilities=missing
            )

        prepared: PreparedRun | None = None
        evidence: EvidenceBundle | None = None
        result: RunResult
        adapter_error: str | None = None
        executed = False
        try:
            prepared = adapter.prepare(scenario)
            executed = True
            adapter.execute(prepared)
            evidence = adapter.collect(prepared)
            _validate_binding(scenario, evidence)
            result = self._oracles.score(scenario, evidence)
        except Exception as error:
            result = _invalid_result(error)
            adapter_error = _error_text(error)

        cleanup_error: str | None = None
        if prepared is not None:
            try:
                adapter.cleanup(prepared)
            except Exception as error:
                cleanup_error = _error_text(error)

        return RunRecord(
            result, evidence, executed, adapter_error=adapter_error, cleanup_error=cleanup_error
        )


def rescore(scenario: Scenario, evidence: EvidenceBundle, oracles: OracleRegistry) -> RunResult:
    _validate_binding(scenario, evidence)
    return oracles.score(scenario, evidence)


def _validate_binding(scenario: Scenario, evidence: EvidenceBundle) -> None:
    if evidence.scenario_id != scenario.scenario_id:
        raise ValueError("evidence scenario ID does not match")
    if evidence.scenario_version != scenario.version:
        raise ValueError("evidence scenario version does not match")
    if evidence.scenario_digest != scenario_digest(scenario):
        raise ValueError("evidence scenario digest does not match")


def _unsupported_result(missing: tuple[str, ...]) -> RunResult:
    return RunResult(
        Outcome.NOT_RUN,
        Outcome.NOT_RUN,
        RunClassification.UNSUPPORTED,
        ControlResponse.NOT_OBSERVABLE,
        (f"missing capabilities: {', '.join(missing)}",),
        (),
    )


def _invalid_result(error: Exception) -> RunResult:
    return RunResult(
        Outcome.NOT_RUN,
        Outcome.NOT_RUN,
        RunClassification.INVALID_RUN,
        ControlResponse.NOT_OBSERVABLE,
        (_error_text(error),),
        (),
    )


def _error_text(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"
