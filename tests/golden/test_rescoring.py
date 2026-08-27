from pathlib import Path

import pytest

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.runner import Runner, rescore
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def load(scenario_id: str):
    path = next((ROOT / "scenarios").glob(f"*/*{scenario_id}*/scenario.json"))
    return load_scenario(path, ROOT / "schemas/scenario.schema.json")


def test_stored_evidence_rescores_without_adapter_execution() -> None:
    scenario = load("AUTH-001")
    adapter = ReferenceAdapter(mode="guarded_pass")
    record = Runner(seed_oracle_registry()).run(scenario, adapter)
    assert record.evidence is not None
    calls_after_execution = adapter.calls

    stored = record.evidence.to_json()
    restored = EvidenceBundle.from_json(stored)
    rescored = rescore(scenario, restored, seed_oracle_registry())

    assert rescored == record.result
    assert adapter.calls == calls_after_execution


def test_rescore_rejects_evidence_bound_to_another_scenario() -> None:
    authority = load("AUTH-001")
    mutation = load("MUT-001")
    record = Runner(seed_oracle_registry()).run(authority, ReferenceAdapter(mode="guarded_pass"))
    assert record.evidence is not None
    with pytest.raises(ValueError, match="scenario ID"):
        rescore(mutation, record.evidence, seed_oracle_registry())
