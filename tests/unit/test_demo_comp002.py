from pathlib import Path

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.result import ControlResponse, Outcome, RunClassification
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def _scenario():
    return load_scenario(
        ROOT / 'scenarios/completion/COMP-002/scenario.json',
        ROOT / 'schemas/scenario.schema.json',
    )


def test_current_verification_mode_emits_admissible_b_bound_evidence() -> None:
    scenario = _scenario()

    record = Runner(seed_oracle_registry()).run(
        scenario,
        ReferenceAdapter(mode='current_verification', root=ROOT),
    )

    assert record.evidence is not None
    verifier = record.evidence.artifacts_of_kind('verifier_record')[0]
    completion = record.evidence.artifacts_of_kind('completion_state')[0]
    source_b = scenario.ground_truth['source_b_digest']
    assert verifier.subject_digest == source_b
    assert verifier.data == {'subject_digest': source_b, 'passed': True}
    assert completion.subject_digest == source_b
    assert completion.data == {'subject_digest': source_b, 'verified': True}
    assert record.result.functional is Outcome.PASS
    assert record.result.control is Outcome.PASS
    assert record.result.control_response is ControlResponse.BEHAVIOR_ONLY
    assert record.result.classification is RunClassification.BEHAVIORAL_PASS
