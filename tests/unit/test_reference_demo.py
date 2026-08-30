from pathlib import Path

from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.reference_demo import run_reference_demo
from agentic_conformance.runner import rescore
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def test_reference_demo_writes_offline_rescorable_evidence(tmp_path: Path) -> None:
    output = tmp_path / "auth-001-reference-evidence.json"
    summary = run_reference_demo(ROOT, output)

    assert summary["scenario"] == "AUTH-001@1.0.0"
    assert summary["classification"] == "GUARDED_PASS"
    assert summary["offline_rescore_equal"] is True
    assert summary["evidence_path"] == str(output.resolve())

    restored = EvidenceBundle.from_json(output.read_text(encoding="utf-8"))
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    rescored = rescore(scenario, restored, seed_oracle_registry())
    assert rescored.classification.value == "GUARDED_PASS"
