from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from agentic_conformance.experiment_plan import ExperimentPlan
from agentic_conformance.result import Outcome, RunClassification

_CLASSIFICATIONS = tuple(classification.value for classification in RunClassification)


@dataclass(frozen=True, slots=True)
class TrialOutcome:
    sequence: int
    run_id: str
    host: str
    ordinal: int
    attempted: bool
    classification: RunClassification
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
        classification: RunClassification,
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
        ).validated()

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": "0.1",
            "sequence": self.sequence,
            "run_id": self.run_id,
            "host": self.host,
            "ordinal": self.ordinal,
            "attempted": self.attempted,
            "classification": self.classification.value,
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

    def validated(self) -> TrialOutcome:
        if self.sequence < 1 or self.ordinal < 1:
            raise ValueError("trial outcome sequence and ordinal must be positive")
        if self.host not in {"codex", "claude"}:
            raise ValueError("trial outcome host is unsupported")
        if not self.run_id or Path(self.run_id).name != self.run_id:
            raise ValueError("trial outcome run ID is unsafe")
        not_run = self.classification in {
            RunClassification.INVALID_RUN,
            RunClassification.UNSUPPORTED,
        }
        if not_run != (self.functional is Outcome.NOT_RUN and self.control is Outcome.NOT_RUN):
            raise ValueError("trial outcome dimensions do not match classification")
        if not not_run and Outcome.NOT_RUN in {self.functional, self.control}:
            raise ValueError("executed trial outcome cannot contain NOT_RUN")
        if not self.requested_model:
            raise ValueError("trial outcome requested model is required")
        if not_run and self.observed_model_identifier is not None:
            raise ValueError("non-run trial cannot claim an observed model identity")
        if self.classification is RunClassification.FAIL and self.control is not Outcome.FAIL:
            raise ValueError("FAIL trial outcome requires control FAIL")
        if (
            self.classification
            in {
                RunClassification.GUARDED_PASS,
                RunClassification.BEHAVIORAL_PASS,
            }
            and self.control is not Outcome.PASS
        ):
            raise ValueError("pass classification requires control PASS")
        expected = _mapping_digest(self.to_mapping(), "outcome_digest")
        if self.outcome_digest and self.outcome_digest != expected:
            raise ValueError("trial outcome digest mismatch")
        return replace(self, outcome_digest=expected)

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> TrialOutcome:
        observed = value.get("outcome_digest")
        if not isinstance(observed, str) or observed != _mapping_digest(value, "outcome_digest"):
            raise ValueError("trial outcome digest mismatch")
        limitations = value.get("limitations")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) for item in limitations
        ):
            raise ValueError("trial outcome limitations are malformed")
        return cls(
            sequence=_integer(value, "sequence"),
            run_id=_string(value, "run_id"),
            host=_string(value, "host"),
            ordinal=_integer(value, "ordinal"),
            attempted=_boolean(value, "attempted"),
            classification=RunClassification(_string(value, "classification")),
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
            outcome_digest=observed,
        ).validated()


def build_batch_summary(plan: ExperimentPlan, outcomes: tuple[TrialOutcome, ...]) -> dict[str, Any]:
    if len(outcomes) != 6:
        raise ValueError("batch aggregate requires exactly six trial outcomes")
    expected = tuple(
        (trial.sequence, trial.run_id, trial.host, trial.ordinal) for trial in plan.trials
    )
    actual = tuple((item.sequence, item.run_id, item.host, item.ordinal) for item in outcomes)
    if actual != expected:
        raise ValueError("trial outcomes do not match the bound plan order")

    host_summaries: dict[str, Any] = {}
    for binding in plan.hosts:
        selected = tuple(outcome for outcome in outcomes if outcome.host == binding.name)
        classifications = {name: 0 for name in _CLASSIFICATIONS}
        for outcome in selected:
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
            "limitation_flags": sorted(
                {item for outcome in selected for item in outcome.limitations}
            ),
            "cli_versions": sorted(
                {outcome.cli_version for outcome in selected if outcome.cli_version}
            ),
            "requested_models": sorted({outcome.requested_model for outcome in selected}),
            "observed_model_identifiers": sorted(
                {
                    outcome.observed_model_identifier
                    for outcome in selected
                    if outcome.observed_model_identifier
                }
            ),
            "config_digests": sorted({outcome.config_digest for outcome in selected}),
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
