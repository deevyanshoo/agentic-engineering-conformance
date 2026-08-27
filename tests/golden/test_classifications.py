from pathlib import Path

import pytest

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.result import Outcome, RunClassification
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def load(scenario_id: str):
    path = next((ROOT / "scenarios").glob(f"*/*{scenario_id}*/scenario.json"))
    return load_scenario(path, ROOT / "schemas/scenario.schema.json")


@pytest.mark.parametrize(
    ("scenario_id", "mode", "classification"),
    [
        ("AUTH-001", "guarded_pass", RunClassification.GUARDED_PASS),
        ("AUTH-001", "behavioral_pass", RunClassification.BEHAVIORAL_PASS),
        ("COMP-002", "control_violation", RunClassification.FAIL),
        ("AUTH-001", "insufficient_evidence", RunClassification.INCONCLUSIVE),
        ("AUTH-001", "adapter_crash", RunClassification.INVALID_RUN),
        ("AUTH-001", "unsupported", RunClassification.UNSUPPORTED),
    ],
)
def test_all_run_classifications_are_deterministic(
    scenario_id: str, mode: str, classification: RunClassification
) -> None:
    record = Runner(seed_oracle_registry()).run(load(scenario_id), ReferenceAdapter(mode=mode))
    assert record.result.classification is classification


@pytest.mark.parametrize(
    ("mode", "functional", "control"),
    [
        ("guarded_pass", Outcome.PASS, Outcome.PASS),
        ("control_violation", Outcome.FAIL, Outcome.FAIL),
        ("functional_failure", Outcome.FAIL, Outcome.PASS),
        ("functional_and_control_failure", Outcome.FAIL, Outcome.FAIL),
    ],
)
def test_useful_functional_control_combinations(
    mode: str, functional: Outcome, control: Outcome
) -> None:
    record = Runner(seed_oracle_registry()).run(load("MUT-001"), ReferenceAdapter(mode=mode))
    assert (record.result.functional, record.result.control) == (functional, control)


def test_functional_pass_control_fail_combination() -> None:
    result = (
        Runner(seed_oracle_registry())
        .run(load("COMP-002"), ReferenceAdapter(mode="control_violation"))
        .result
    )
    assert (result.functional, result.control) == (Outcome.PASS, Outcome.FAIL)


def test_agent_assertion_alone_is_inconclusive() -> None:
    result = (
        Runner(seed_oracle_registry())
        .run(load("AUTH-001"), ReferenceAdapter(mode="assertion_only"))
        .result
    )
    assert result.classification is RunClassification.INCONCLUSIVE
