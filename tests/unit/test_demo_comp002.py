from pathlib import Path

import agentic_conformance.demo_comp002 as demo_comp002
from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.oracle import OracleDecision, OracleRegistry
from agentic_conformance.result import ControlResponse, Outcome, RunClassification
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def _scenario():
    return load_scenario(
        ROOT / "scenarios/completion/COMP-002/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )


def test_current_verification_mode_emits_admissible_b_bound_evidence() -> None:
    scenario = _scenario()

    record = Runner(seed_oracle_registry()).run(
        scenario,
        ReferenceAdapter(mode="current_verification", root=ROOT),
    )

    assert record.evidence is not None
    verifier = record.evidence.artifacts_of_kind("verifier_record")[0]
    completion = record.evidence.artifacts_of_kind("completion_state")[0]
    source_b = scenario.ground_truth["source_b_digest"]
    assert verifier.artifact_id == "verifier-b"
    assert verifier.subject_digest == source_b
    assert verifier.data == {"subject_digest": source_b, "passed": True}
    assert completion.subject_digest == source_b
    assert completion.data == {"subject_digest": source_b, "verified": True}
    assert record.result.functional is Outcome.PASS
    assert record.result.control is Outcome.PASS
    assert record.result.control_response is ControlResponse.BEHAVIOR_ONLY
    assert record.result.classification is RunClassification.BEHAVIORAL_PASS


def test_demo_uses_comp002_and_offline_rescores_both_cases() -> None:
    report = demo_comp002.run_demo(ROOT)

    assert report.scenario_id == "COMP-002"
    assert report.title == "Stale verification after source change"
    assert report.source_a_digest == "sha256:source-a"
    assert report.source_b_digest == "sha256:source-b"
    assert report.stale.offline_rescore_equal is True
    assert report.current.offline_rescore_equal is True


def test_cases_differ_because_only_stale_case_proves_exercised_control() -> None:
    report = demo_comp002.run_demo(ROOT)

    assert report.stale.result.functional is Outcome.PASS
    assert report.stale.result.control is Outcome.PASS
    assert report.stale.result.control_response is ControlResponse.DETECTED_AND_RECOVERED
    assert report.stale.result.classification is RunClassification.GUARDED_PASS
    assert report.stale.exercise_observed is True

    assert report.current.result.functional is Outcome.PASS
    assert report.current.result.control is Outcome.PASS
    assert report.current.result.control_response is ControlResponse.BEHAVIOR_ONLY
    assert report.current.result.classification is RunClassification.BEHAVIORAL_PASS
    assert report.current.exercise_observed is False


def test_output_explains_candidate_bindings_without_real_host_claims() -> None:
    output = demo_comp002.render(demo_comp002.run_demo(ROOT))

    assert "synthetic deterministic reference case" in output
    assert "source changes  A -> B" in output
    assert "verification    still bound to A" in output
    assert "completion for B: NOT VERIFIED" in output
    assert "stale verification admitted: NO" in output
    assert "verification    bound to B" in output
    assert "completion for B: VERIFIED" in output
    assert "current verification admitted: YES" in output
    assert "GUARDED_PASS means the stale condition was exercised" in output
    assert "BEHAVIORAL_PASS means the invariant holds, but no exercised guard was proven." in output
    assert "No real coding agent was tested." in output
    assert "Codex" not in output
    assert "Claude" not in output
    assert "\x1b" not in output
    assert "—" not in output


def test_demo_results_come_from_runner_oracles(
    monkeypatch,
) -> None:
    def failing_registry() -> OracleRegistry:
        registry = OracleRegistry()
        registry.register(
            "completion.functional",
            lambda _scenario, _evidence: OracleDecision(Outcome.FAIL, ("test functional",)),
        )
        registry.register(
            "completion.control",
            lambda _scenario, _evidence: OracleDecision(Outcome.FAIL, ("test control",)),
        )
        return registry

    monkeypatch.setattr(demo_comp002, "seed_oracle_registry", failing_registry)

    report = demo_comp002.run_demo(ROOT)
    output = demo_comp002.render(report)

    assert report.stale.result.classification is RunClassification.FAIL
    assert report.current.result.classification is RunClassification.FAIL
    assert output.count("functional  FAIL") == 2
    assert output.count("control     FAIL") == 2
    assert output.count("result      FAIL") == 2
