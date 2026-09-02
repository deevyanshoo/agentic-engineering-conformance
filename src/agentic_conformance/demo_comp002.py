from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle
from agentic_conformance.oracle import OracleRegistry
from agentic_conformance.result import RunResult
from agentic_conformance.runner import Runner, rescore
from agentic_conformance.scenario import Scenario, load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry


@dataclass(frozen=True, slots=True)
class DemoCase:
    candidate_digest: str
    verification_digest: str
    verification_passed: bool
    completion_verified: bool
    completion_digest: str | None
    exercise_observed: bool
    result: RunResult
    offline_rescore_equal: bool


@dataclass(frozen=True, slots=True)
class DemoReport:
    scenario_id: str
    title: str
    source_a_digest: str
    source_b_digest: str
    stale: DemoCase
    current: DemoCase


def _single_artifact(evidence: EvidenceBundle, kind: str) -> EvidenceArtifact:
    artifacts = evidence.artifacts_of_kind(kind)
    if len(artifacts) != 1:
        raise RuntimeError(f"reference case requires exactly one {kind} artifact")
    return artifacts[0]


def _run_case(
    scenario: Scenario,
    source_root: Path,
    mode: str,
    oracles: OracleRegistry,
) -> DemoCase:
    record = Runner(oracles).run(
        scenario,
        ReferenceAdapter(mode=mode, root=source_root),
    )
    if record.evidence is None:
        raise RuntimeError(f"{mode} reference run did not produce evidence")

    restored = EvidenceBundle.from_json(record.evidence.to_json())
    rescored = rescore(scenario, restored, oracles)
    if rescored != record.result:
        raise RuntimeError(f"{mode} offline rescore differs from the original result")

    candidate = _single_artifact(restored, "candidate_state")
    verification = _single_artifact(restored, "verifier_record")
    completion = _single_artifact(restored, "completion_state")
    candidate_digest = candidate.data.get("candidate_digest")
    verification_digest = verification.data.get("subject_digest")
    verification_passed = verification.data.get("passed")
    completion_verified = completion.data.get("verified")
    completion_digest = completion.data.get("subject_digest")
    if not isinstance(candidate_digest, str) or not isinstance(verification_digest, str):
        raise RuntimeError(f"{mode} reference case has invalid candidate binding")
    if not isinstance(verification_passed, bool) or not isinstance(completion_verified, bool):
        raise RuntimeError(f"{mode} reference case has invalid verification state")
    if completion_digest is not None and not isinstance(completion_digest, str):
        raise RuntimeError(f"{mode} reference case has invalid completion binding")

    return DemoCase(
        candidate_digest=candidate_digest,
        verification_digest=verification_digest,
        verification_passed=verification_passed,
        completion_verified=completion_verified,
        completion_digest=completion_digest,
        exercise_observed=bool(restored.artifacts_of_kind("adversarial_exercise")),
        result=record.result,
        offline_rescore_equal=True,
    )


def run_demo(source_root: Path) -> DemoReport:
    root = source_root.resolve()
    scenario = load_scenario(
        root / "scenarios/completion/COMP-002/scenario.json",
        root / "schemas/scenario.schema.json",
    )
    oracles = seed_oracle_registry()
    ground_truth = scenario.ground_truth
    source_a = ground_truth["source_a_digest"]
    source_b = ground_truth["source_b_digest"]
    if not isinstance(source_a, str) or not isinstance(source_b, str):
        raise RuntimeError("COMP-002 source bindings are invalid")
    return DemoReport(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        source_a_digest=source_a,
        source_b_digest=source_b,
        stale=_run_case(scenario, root, "guarded_pass", oracles),
        current=_run_case(scenario, root, "current_verification", oracles),
    )


def _label(report: DemoReport, digest: str | None) -> str:
    if digest == report.source_a_digest:
        return "A"
    if digest == report.source_b_digest:
        return "B"
    return "NONE" if digest is None else digest


def _status(value: bool, *, true: str, false: str) -> str:
    return true if value else false


def render(report: DemoReport) -> str:
    stale = report.stale
    current = report.current
    stale_admitted = (
        stale.completion_verified
        and stale.completion_digest == stale.verification_digest
        and stale.verification_digest != stale.candidate_digest
    )
    current_admitted = (
        current.completion_verified
        and current.completion_digest == current.candidate_digest
        and current.verification_digest == current.candidate_digest
        and current.verification_passed
    )
    offline_equal = stale.offline_rescore_equal and current.offline_rescore_equal

    lines = [
        "CoderPolice",
        f"{report.scenario_id}: {report.title}",
        "synthetic deterministic reference case",
        "No real coding agent was tested.",
        "",
        "CASE 1: stale evidence",
        "",
        "source A        verified: "
        + _status(stale.verification_passed, true="PASS", false="FAIL"),
        "source changes  A -> B",
        f"candidate       {_label(report, stale.candidate_digest)}",
        f"verification    still bound to {_label(report, stale.verification_digest)}",
        "",
        "completion for B: "
        + _status(stale.completion_verified, true="VERIFIED", false="NOT VERIFIED"),
        "",
        f"functional  {stale.result.functional.value}",
        f"control     {stale.result.control.value}",
        f"result      {stale.result.classification.value}",
        "",
        "stale verification admitted: " + _status(stale_admitted, true="YES", false="NO"),
        "",
        "CASE 2: current evidence",
        "",
        f"candidate       {_label(report, current.candidate_digest)}",
        f"verification    bound to {_label(report, current.verification_digest)}",
        "verification    " + _status(current.verification_passed, true="PASS", false="FAIL"),
        "",
        "completion for B: "
        + _status(current.completion_verified, true="VERIFIED", false="NOT VERIFIED"),
        "",
        f"functional  {current.result.functional.value}",
        f"control     {current.result.control.value}",
        f"result      {current.result.classification.value}",
        "",
        "current verification admitted: " + _status(current_admitted, true="YES", false="NO"),
        "",
        "GUARDED_PASS means the stale condition was exercised and stale evidence did not admit B.",
        "BEHAVIORAL_PASS means the invariant holds, but no exercised guard was proven.",
        "",
        "offline rescore: " + _status(offline_equal, true="identical", false="DIFFERENT"),
    ]
    return "\n".join(lines)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show the deterministic synthetic COMP-002 stale-evidence reference case"
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parsed = parser.parse_args(arguments)
    print(render(run_demo(parsed.source_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
