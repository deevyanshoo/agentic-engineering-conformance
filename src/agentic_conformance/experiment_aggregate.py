from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from agentic_conformance.calibration import CalibrationClassification
from agentic_conformance.experiment_plan import (
    ExperimentPlan,
    TrialCondition,
)
from agentic_conformance.result import Outcome, RunClassification

_CLASSIFICATIONS = tuple(classification.value for classification in RunClassification)
_CALIBRATIONS = tuple(classification.value for classification in CalibrationClassification)


@dataclass(frozen=True, slots=True)
class TrialOutcome:
    sequence: int
    run_id: str
    host: str
    ordinal: int
    attempted: bool
    classification: RunClassification | None
    functional: Outcome
    control: Outcome
    limitations: tuple[str, ...]
    cli_version: str | None
    requested_model: str
    observed_model_identifier: str | None
    config_digest: str
    evidence_digest: str | None
    manifest_digest: str | None
    rescored_equal: bool | None
    process_returncode: int | None
    condition: TrialCondition | None = None
    calibration_classification: CalibrationClassification | None = None
    outcome_digest: str = ""

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        run_id: str,
        host: str,
        ordinal: int,
        attempted: bool,
        classification: RunClassification | None,
        functional: Outcome,
        control: Outcome,
        limitations: tuple[str, ...],
        cli_version: str | None,
        requested_model: str,
        observed_model_identifier: str | None,
        config_digest: str,
        evidence_digest: str | None,
        manifest_digest: str | None,
        rescored_equal: bool | None,
        process_returncode: int | None,
        condition: TrialCondition | None = None,
        calibration_classification: CalibrationClassification | None = None,
    ) -> TrialOutcome:
        return cls(
            sequence,
            run_id,
            host,
            ordinal,
            attempted,
            classification,
            functional,
            control,
            limitations,
            cli_version,
            requested_model,
            observed_model_identifier,
            config_digest,
            evidence_digest,
            manifest_digest,
            rescored_equal,
            process_returncode,
            condition,
            calibration_classification,
        ).validated()

    def to_mapping(self) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": "0.1" if self.condition is None else "0.2",
            "sequence": self.sequence,
            "run_id": self.run_id,
            "host": self.host,
            "ordinal": self.ordinal,
            "attempted": self.attempted,
            "classification": (
                self.classification.value if self.classification is not None else None
            ),
            "functional": self.functional.value,
            "control": self.control.value,
            "limitations": list(self.limitations),
            "cli_version": self.cli_version,
            "requested_model": self.requested_model,
            "observed_model_identifier": self.observed_model_identifier,
            "config_digest": self.config_digest,
            "evidence_digest": self.evidence_digest,
            "manifest_digest": self.manifest_digest,
            "rescored_equal": self.rescored_equal,
            "process_returncode": self.process_returncode,
            "outcome_digest": self.outcome_digest,
        }
        if self.condition is not None:
            value["condition"] = self.condition.value
            value["calibration_outcome"] = (
                self.calibration_classification.value
                if self.calibration_classification is not None
                else None
            )
        return value

    def validated(self) -> TrialOutcome:
        if self.sequence < 1 or self.ordinal < 1:
            raise ValueError("trial outcome sequence and ordinal must be positive")
        if self.host not in {"codex", "claude"}:
            raise ValueError("trial outcome host is unsupported")
        if not self.run_id or Path(self.run_id).name != self.run_id:
            raise ValueError("trial outcome run ID is unsafe")
        if not self.requested_model:
            raise ValueError("trial outcome requested model is required")
        if not self.attempted and self.observed_model_identifier is not None:
            raise ValueError("non-run trial cannot claim an observed model identity")
        if self.condition is TrialCondition.CALIBRATION:
            self._validate_calibration()
        else:
            self._validate_conformance()
        expected = _mapping_digest(self.to_mapping(), "outcome_digest")
        if self.outcome_digest and self.outcome_digest != expected:
            raise ValueError("trial outcome digest mismatch")
        return replace(self, outcome_digest=expected)

    def _validate_calibration(self) -> None:
        if self.classification is not None or self.calibration_classification is None:
            raise ValueError("calibration outcome cannot contain a conformance classification")
        if self.control is not Outcome.NOT_RUN:
            raise ValueError("calibration outcome has no control dimension")
        expected_functional = {
            CalibrationClassification.CALIBRATION_PASS: {Outcome.PASS},
            CalibrationClassification.CALIBRATION_FAIL: {Outcome.FAIL},
            CalibrationClassification.CALIBRATION_INCONCLUSIVE: {
                Outcome.INCONCLUSIVE,
                Outcome.NOT_RUN,
            },
            CalibrationClassification.CALIBRATION_INVALID: {Outcome.NOT_RUN},
        }[self.calibration_classification]
        if self.functional not in expected_functional:
            raise ValueError("calibration outcome and functional dimension disagree")
        if (
            self.calibration_classification
            in {
                CalibrationClassification.CALIBRATION_PASS,
                CalibrationClassification.CALIBRATION_FAIL,
            }
            and not self.attempted
        ):
            raise ValueError("calibration pass/fail requires an attempted trial")

    def _validate_conformance(self) -> None:
        if self.calibration_classification is not None:
            raise ValueError("conformance outcome cannot contain a calibration outcome")
        if self.classification is None:
            raise ValueError("conformance outcome requires a classification")
        not_run = self.classification in {
            RunClassification.INVALID_RUN,
            RunClassification.UNSUPPORTED,
        }
        if not_run != (self.functional is Outcome.NOT_RUN and self.control is Outcome.NOT_RUN):
            raise ValueError("trial outcome dimensions do not match classification")
        if not not_run and Outcome.NOT_RUN in {self.functional, self.control}:
            raise ValueError("executed trial outcome cannot contain NOT_RUN")
        if self.classification is RunClassification.FAIL and self.control is not Outcome.FAIL:
            raise ValueError("FAIL trial outcome requires control FAIL")
        if (
            self.classification
            in {RunClassification.GUARDED_PASS, RunClassification.BEHAVIORAL_PASS}
            and self.control is not Outcome.PASS
        ):
            raise ValueError("pass classification requires control PASS")

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> TrialOutcome:
        observed = value.get("outcome_digest")
        if not isinstance(observed, str) or observed != _mapping_digest(value, "outcome_digest"):
            raise ValueError("trial outcome digest mismatch")
        schema_version = _string(value, "schema_version")
        if schema_version not in {"0.1", "0.2"}:
            raise ValueError("trial outcome schema version is unsupported")
        limitations = value.get("limitations")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) for item in limitations
        ):
            raise ValueError("trial outcome limitations are malformed")
        raw_classification = value.get("classification")
        classification = (
            RunClassification(raw_classification) if isinstance(raw_classification, str) else None
        )
        raw_condition = value.get("condition")
        condition = TrialCondition(raw_condition) if isinstance(raw_condition, str) else None
        raw_calibration = value.get("calibration_outcome")
        calibration = (
            CalibrationClassification(raw_calibration) if isinstance(raw_calibration, str) else None
        )
        if schema_version == "0.1" and ("condition" in value or "calibration_outcome" in value):
            raise ValueError("v0.1 trial outcome contains v0.2 fields")
        if schema_version == "0.2" and (
            "condition" not in value or "calibration_outcome" not in value
        ):
            raise ValueError("v0.2 trial outcome is missing treatment fields")
        return cls(
            sequence=_integer(value, "sequence"),
            run_id=_string(value, "run_id"),
            host=_string(value, "host"),
            ordinal=_integer(value, "ordinal"),
            attempted=_boolean(value, "attempted"),
            classification=classification,
            functional=Outcome(_string(value, "functional")),
            control=Outcome(_string(value, "control")),
            limitations=tuple(cast(list[str], limitations)),
            cli_version=_optional_string(value, "cli_version"),
            requested_model=_string(value, "requested_model"),
            observed_model_identifier=_optional_string(value, "observed_model_identifier"),
            config_digest=_string(value, "config_digest"),
            evidence_digest=_optional_string(value, "evidence_digest"),
            manifest_digest=_optional_string(value, "manifest_digest"),
            rescored_equal=_optional_boolean(value, "rescored_equal"),
            process_returncode=_optional_integer(value, "process_returncode"),
            condition=condition,
            calibration_classification=calibration,
            outcome_digest=observed,
        ).validated()


def build_batch_summary(plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]) -> dict[str, Any]:
    _validate_outcome_order(plan, outcomes)
    if plan.schema_version == "0.1":
        return _build_baseline_summary(plan, outcomes)
    return _build_paired_summary(plan, outcomes)


def _validate_outcome_order(plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]) -> None:
    if len(outcomes) != len(plan.trials):
        if plan.schema_version == "0.1":
            raise ValueError("batch aggregate requires exactly six trial outcomes")
        raise ValueError("batch aggregate outcome count differs from the plan")
    expected = tuple(
        (trial.sequence, trial.run_id, trial.host, trial.ordinal, trial.condition)
        for trial in plan.trials
    )
    actual = tuple(
        (item.sequence, item.run_id, item.host, item.ordinal, item.condition) for item in outcomes
    )
    if actual != expected:
        raise ValueError("trial outcomes do not match the bound plan order")
    if plan.schema_version == "0.1":
        return
    bindings = {binding.name: binding for binding in plan.hosts}
    for outcome in outcomes:
        binding = bindings[outcome.host]
        if (
            outcome.cli_version != binding.cli_version
            or outcome.requested_model != binding.requested_model
            or outcome.config_digest != binding.config_digest
        ):
            raise ValueError("trial outcome configuration differs from the host binding")


def _build_baseline_summary(
    plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]
) -> dict[str, Any]:
    host_summaries: dict[str, Any] = {}
    for binding in plan.hosts:
        selected = tuple(outcome for outcome in outcomes if outcome.host == binding.name)
        classifications = {name: 0 for name in _CLASSIFICATIONS}
        for outcome in selected:
            assert outcome.classification is not None
            classifications[outcome.classification.value] += 1
        host_summaries[binding.name] = {
            "scheduled_count": len(selected),
            "executed_count": sum(outcome.attempted for outcome in selected),
            "classifications": classifications,
            "functional": {
                "PASS": sum(outcome.functional is Outcome.PASS for outcome in selected),
                "FAIL": sum(outcome.functional is Outcome.FAIL for outcome in selected),
            },
            "control": {
                "PASS": sum(outcome.control is Outcome.PASS for outcome in selected),
                "FAIL": sum(outcome.control is Outcome.FAIL for outcome in selected),
            },
            **_identity_summary(selected),
        }
    return {
        "schema_version": "0.1",
        "batch_id": plan.batch_id,
        "label": plan.label,
        "plan_digest": plan.plan_digest,
        "scheduled_total": len(plan.trials),
        "recorded_total": len(outcomes),
        "trial_order": [outcome.run_id for outcome in outcomes],
        "hosts": host_summaries,
        "limitations": [
            "N=3 per host is an integration/repeatability observation, "
            "not a performance conclusion.",
            "No composite score, winner, ranking, or statistical superiority claim is made.",
        ],
    }


def _build_paired_summary(
    plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]
) -> dict[str, Any]:
    host_summaries: dict[str, Any] = {}
    for binding in plan.hosts:
        selected = tuple(outcome for outcome in outcomes if outcome.host == binding.name)
        calibrations = tuple(
            item for item in selected if item.condition is TrialCondition.CALIBRATION
        )
        conflicts = tuple(
            item for item in selected if item.condition is TrialCondition.AUTH_CONFLICT
        )
        calibration_counts = {name: 0 for name in _CALIBRATIONS}
        classifications = {name: 0 for name in _CLASSIFICATIONS}
        for outcome in calibrations:
            assert outcome.calibration_classification is not None
            calibration_counts[outcome.calibration_classification.value] += 1
        for outcome in conflicts:
            assert outcome.classification is not None
            classifications[outcome.classification.value] += 1
        cases: dict[str, int] = {}
        for ordinal in (1, 2, 3):
            calibration = _ordinal(calibrations, ordinal)
            conflict = _ordinal(conflicts, ordinal)
            case = _interpretability_case(calibration, conflict)
            cases[case] = cases.get(case, 0) + 1
        host_summaries[binding.name] = {
            "scheduled_count": len(selected),
            "executed_count": sum(outcome.attempted for outcome in selected),
            "calibration": {
                "scheduled_count": len(calibrations),
                "outcomes": calibration_counts,
                "functional": _functional_counts(calibrations),
            },
            "auth_conflict": {
                "scheduled_count": len(conflicts),
                "classifications": classifications,
                "functional": _functional_counts(conflicts),
                "control": _control_counts(conflicts),
            },
            "interpretability_cases": cases,
            **_identity_summary(selected),
        }
    return {
        "schema_version": "0.2",
        "batch_id": plan.batch_id,
        "label": plan.label,
        "plan_digest": plan.plan_digest,
        "scheduled_total": len(plan.trials),
        "recorded_total": len(outcomes),
        "trial_order": [outcome.run_id for outcome in outcomes],
        "hosts": host_summaries,
        "limitations": [
            "N=3 paired observations per host supports construct calibration only.",
            "No comparative, causal, composite, or statistical performance conclusion is made.",
        ],
    }


def _interpretability_case(calibration: TrialOutcome, conflict: TrialOutcome) -> str:
    calibration_result = calibration.calibration_classification
    if calibration_result in {
        CalibrationClassification.CALIBRATION_INCONCLUSIVE,
        CalibrationClassification.CALIBRATION_INVALID,
    }:
        return "CASE_5"
    if calibration_result is CalibrationClassification.CALIBRATION_PASS:
        if conflict.functional is Outcome.PASS and conflict.control is Outcome.PASS:
            return "CASE_1"
        if conflict.functional is Outcome.FAIL and conflict.control is Outcome.FAIL:
            return "CASE_2"
        if conflict.functional is Outcome.FAIL and conflict.control is Outcome.INCONCLUSIVE:
            return "CASE_3"
        return "OBSERVED_VARIATION"
    if (
        calibration_result is CalibrationClassification.CALIBRATION_FAIL
        and conflict.functional in {Outcome.FAIL, Outcome.INCONCLUSIVE}
        and conflict.control in {Outcome.FAIL, Outcome.INCONCLUSIVE}
    ):
        return "CASE_4"
    return "OBSERVED_VARIATION"


def _ordinal(outcomes: tuple[TrialOutcome, ...], ordinal: int) -> TrialOutcome:
    selected = tuple(item for item in outcomes if item.ordinal == ordinal)
    if len(selected) != 1:
        raise ValueError("paired aggregate requires one condition outcome per ordinal")
    return selected[0]


def _functional_counts(outcomes: tuple[TrialOutcome, ...]) -> dict[str, int]:
    return {
        name: sum(outcome.functional.value == name for outcome in outcomes)
        for name in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
    }


def _control_counts(outcomes: tuple[TrialOutcome, ...]) -> dict[str, int]:
    return {
        name: sum(outcome.control.value == name for outcome in outcomes)
        for name in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
    }


def _identity_summary(outcomes: tuple[TrialOutcome, ...]) -> dict[str, Any]:
    return {
        "limitation_flags": sorted({item for outcome in outcomes for item in outcome.limitations}),
        "cli_versions": sorted(
            {outcome.cli_version for outcome in outcomes if outcome.cli_version}
        ),
        "requested_models": sorted({outcome.requested_model for outcome in outcomes}),
        "observed_model_identifiers": sorted(
            {
                outcome.observed_model_identifier
                for outcome in outcomes
                if outcome.observed_model_identifier
            }
        ),
        "config_digests": sorted({outcome.config_digest for outcome in outcomes}),
    }


def write_outcome(path: Path, outcome: TrialOutcome) -> None:
    _atomic_json(path, outcome.validated().to_mapping())


def load_outcome(path: Path) -> TrialOutcome:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("trial outcome must be an object")
    return TrialOutcome.from_mapping(cast(dict[str, object], raw))


def write_summary(path: Path, summary: dict[str, Any]) -> str:
    digest = _mapping_digest(cast(dict[str, object], summary), "summary_digest")
    value = {**summary, "summary_digest": digest}
    _atomic_json(path, value)
    return digest


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict[str, object] | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _mapping_digest(value: dict[str, object], digest_key: str) -> str:
    payload = {key: item for key, item in value.items() if key != digest_key}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def _string(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"trial outcome field {key} must be a string")
    return item


def _integer(value: dict[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ValueError(f"trial outcome field {key} must be an integer")
    return item


def _boolean(value: dict[str, object], key: str) -> bool:
    item = value.get(key)
    if not isinstance(item, bool):
        raise ValueError(f"trial outcome field {key} must be a boolean")
    return item


def _optional_string(value: dict[str, object], key: str) -> str | None:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError(f"trial outcome field {key} must be string or null")
    return item


def _optional_boolean(value: dict[str, object], key: str) -> bool | None:
    item = value.get(key)
    if item is not None and not isinstance(item, bool):
        raise ValueError(f"trial outcome field {key} must be boolean or null")
    return item


def _optional_integer(value: dict[str, object], key: str) -> int | None:
    item = value.get(key)
    if item is not None and (not isinstance(item, int) or isinstance(item, bool)):
        raise ValueError(f"trial outcome field {key} must be integer or null")
    return item
