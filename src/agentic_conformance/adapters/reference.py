from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.runner import scenario_digest
from agentic_conformance.scenario import Scenario

DEFAULT_CAPABILITIES = frozenset(
    {
        "filesystem.read",
        "filesystem.write",
        "logical_workers.concurrent",
        "candidate.identity",
        "external.verifier",
        "review.identity",
        "dependency.state",
        "durable_state.read",
    }
)


class ReferenceAdapter(Adapter):
    """Deterministic benchmark self-test adapter; it supplies no controls or scores."""

    name = "reference"
    version = "0.1.0"

    def __init__(
        self,
        mode: str,
        capabilities: frozenset[str] | None = None,
        root: Path | None = None,
    ) -> None:
        self.mode = mode
        self.capabilities = capabilities if capabilities is not None else DEFAULT_CAPABILITIES
        self.root = root or Path.cwd()
        self._calls: list[str] = []
        self._prepared: dict[str, Scenario] = {}

    @property
    def calls(self) -> tuple[str, ...]:
        return tuple(self._calls)

    def probe(self) -> frozenset[str]:
        self._calls.append("probe")
        return frozenset() if self.mode == "unsupported" else self.capabilities

    def prepare(self, scenario: Scenario) -> PreparedRun:
        self._calls.append("prepare")
        token = f"{scenario.scenario_id}:{len(self._prepared)}"
        self._prepared[token] = scenario
        return PreparedRun(token)

    def execute(self, prepared: PreparedRun) -> None:
        self._calls.append("execute")
        if self.mode == "adapter_crash":
            raise RuntimeError("synthetic reference adapter crash")
        if prepared.token not in self._prepared:
            raise ValueError("unknown prepared run")

    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        self._calls.append("collect")
        scenario = self._prepared[prepared.token]
        fixture = self._load_fixture(scenario)
        artifacts = _seed_artifacts(scenario, self.mode, fixture)
        return EvidenceBundle.create(
            scenario.scenario_id,
            scenario.version,
            scenario_digest(scenario),
            fixture,
            artifacts,
            ("deterministic reference adapter; not an external host measurement",),
        )

    def cleanup(self, prepared: PreparedRun) -> None:
        self._calls.append("cleanup")
        self._prepared.pop(prepared.token, None)

    def _load_fixture(self, scenario: Scenario) -> dict[str, Any]:
        fixture_contract = scenario.definition["fixture"]
        path = self.root / fixture_contract["path"]
        raw = path.read_bytes()
        observed_digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"
        if observed_digest != fixture_contract["digest"]:
            raise ValueError("fixture digest does not match scenario binding")
        value: dict[str, Any] = json.loads(raw)
        return value


def _artifact(
    artifact_id: str,
    kind: str,
    data: dict[str, Any],
    level: EvidenceLevel = EvidenceLevel.E1,
    subject_digest: str | None = None,
    producer: str | None = None,
) -> EvidenceArtifact:
    if producer is None:
        producer = "AGENT" if level is EvidenceLevel.E4 else "ADAPTER_OBSERVER"
    return EvidenceArtifact.create(artifact_id, level, kind, producer, data, subject_digest)


def _exercise_and_event(response: str, scenario: Scenario) -> list[EvidenceArtifact]:
    condition = scenario.definition["exercise_condition"]
    subject = scenario_digest(scenario)
    exercise = _artifact(
        "exercise",
        condition["kind"],
        {condition["field"]: condition["equals"]},
        subject_digest=subject,
    )
    event = _artifact(
        "control",
        "control_event",
        {"response": response, "exercise_digest": exercise.digest},
        EvidenceLevel.E2,
        subject,
        "HOST_LIFECYCLE",
    )
    return [exercise, event]


def _with_control(
    core: list[EvidenceArtifact], mode: str, response: str, scenario: Scenario
) -> tuple[EvidenceArtifact, ...]:
    if mode == "guarded_pass":
        core.extend(_exercise_and_event(response, scenario))
    elif mode in {
        "control_violation",
        "functional_and_control_failure",
        "under_invalidation",
        "over_invalidation",
        "inconsistent_state",
    }:
        condition = scenario.definition["exercise_condition"]
        core.append(
            _artifact(
                "exercise",
                condition["kind"],
                {condition["field"]: condition["equals"]},
                subject_digest=scenario_digest(scenario),
            )
        )
    return tuple(core)


def _seed_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    if mode == "insufficient_evidence":
        return ()
    if mode == "assertion_only":
        return (
            _artifact(
                "agent-claim",
                "final_behavior",
                {"behavior": fixture.get("current_behavior", "B")},
                EvidenceLevel.E4,
            ),
        )
    if scenario.scenario_id == "AUTH-001":
        return _authority_artifacts(scenario, mode, fixture)
    if scenario.scenario_id == "MUT-001":
        return _mutation_artifacts(scenario, mode, fixture)
    if scenario.scenario_id == "COMP-002":
        return _completion_artifacts(scenario, mode, fixture)
    if scenario.scenario_id == "REV-002":
        return _review_artifacts(scenario, mode, fixture)
    if scenario.scenario_id == "INV-003":
        return _invalidation_artifacts(scenario, mode, fixture)
    if scenario.scenario_id == "REC-001":
        return _reconstruction_artifacts(scenario, mode, fixture)
    raise ValueError(f"unsupported reference scenario: {scenario.scenario_id}")


def _authority_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    violation = mode in {"control_violation", "functional_and_control_failure"}
    behavior = fixture["stale_behavior"] if violation else fixture["current_behavior"]
    core = [_artifact("final", "final_behavior", {"behavior": behavior})]
    return _with_control(core, mode, "PREVENTED", scenario)


def _mutation_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    intended = fixture["intended_changes"]
    functional_failure = mode in {
        "control_violation",
        "functional_failure",
        "functional_and_control_failure",
    }
    changes = {"worker_one": intended["worker_one"]} if functional_failure else intended
    coordinated = mode not in {"control_violation", "functional_and_control_failure"}
    core = [
        _artifact("final", "final_shared_state", {"changes": changes}),
        _artifact(
            "disposition",
            "mutation_disposition",
            {"coordinated": coordinated, "overlapping_path": fixture["overlapping_path"]},
        ),
    ]
    return _with_control(core, mode, "SERIALIZED", scenario)


def _completion_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    candidate = fixture["source_b_digest"]
    stale = fixture["source_a_digest"]
    functional = mode not in {"functional_failure", "functional_and_control_failure"}
    admitted_stale = mode in {"control_violation", "functional_and_control_failure"}
    current_verification = mode == "current_verification"
    verification_subject = candidate if current_verification else stale
    verifier_id = "verifier-b" if current_verification else "verifier-a"
    verified = admitted_stale or current_verification
    core = [
        _artifact(
            "candidate",
            "candidate_state",
            {"candidate_digest": candidate, "functional": functional},
            subject_digest=candidate,
        ),
        _artifact(
            verifier_id,
            "verifier_record",
            {"subject_digest": verification_subject, "passed": True},
            subject_digest=verification_subject,
        ),
        _artifact(
            "completion",
            "completion_state",
            {"verified": verified, "subject_digest": verification_subject if verified else None},
            subject_digest=candidate,
        ),
    ]
    return _with_control(core, mode, "DETECTED_AND_RECOVERED", scenario)


def _review_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    candidate = fixture["candidate_b_digest"]
    stale = fixture["candidate_a_digest"]
    functional = mode not in {"functional_failure", "functional_and_control_failure"}
    admitted_stale = mode in {"control_violation", "functional_and_control_failure"}
    core = [
        _artifact(
            "candidate",
            "candidate_state",
            {"candidate_digest": candidate, "functional": functional},
            subject_digest=candidate,
        ),
        _artifact(
            "review-a",
            "review_record",
            {"subject_digest": stale, "approved": True, "independent": True},
            subject_digest=stale,
        ),
        _artifact(
            "review-state",
            "review_state",
            {
                "review_satisfied": admitted_stale,
                "subject_digest": stale if admitted_stale else None,
            },
            subject_digest=candidate,
        ),
    ]
    return _with_control(core, mode, "DETECTED_AND_RECOVERED", scenario)


def _invalidation_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    expected_invalidated = list(fixture["expected_invalidated"])
    expected_valid = list(fixture["expected_unaffected"])
    if mode in {"under_invalidation", "control_violation"}:
        invalidated = ["B"]
        valid = sorted(set(expected_valid) | {"D"})
    elif mode in {"over_invalidation", "functional_and_control_failure"}:
        invalidated = sorted(set(expected_invalidated) | {"C"})
        valid = sorted(set(expected_valid) - {"C"})
    else:
        invalidated = expected_invalidated
        valid = expected_valid
    applied = mode not in {"functional_failure", "functional_and_control_failure"}
    core = [
        _artifact("mutation", "mutation_state", {"node": fixture["mutated"], "applied": applied}),
        _artifact(
            "invalidation",
            "invalidation_state",
            {"invalidated": invalidated, "valid": valid},
        ),
    ]
    return _with_control(core, mode, "DETECTED_AND_RECOVERED", scenario)


def _reconstruction_artifacts(
    scenario: Scenario, mode: str, fixture: dict[str, Any]
) -> tuple[EvidenceArtifact, ...]:
    durable = fixture["durable_state"]
    reconstruction = fixture["expected_reconstruction"]
    if mode == "missing_state":
        return (_artifact("reconstruction", "reconstruction", reconstruction),)
    if mode in {"inconsistent_state", "control_violation", "functional_and_control_failure"}:
        reconstruction = dict(reconstruction)
        reconstruction["completed_nodes"] = ["D1", "D2"]
    core = [
        _artifact("durable", "durable_state", durable),
        _artifact("reconstruction", "reconstruction", reconstruction),
    ]
    return _with_control(core, mode, "DETECTED_AND_RECOVERED", scenario)
