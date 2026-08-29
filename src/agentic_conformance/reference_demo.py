from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.runner import Runner, rescore
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry


def run_reference_demo(source_root: Path, output_path: Path) -> dict[str, object]:
    """Execute and offline-rescore the deterministic AUTH-001 reference case."""
    root = source_root.resolve()
    scenario = load_scenario(
        root / "scenarios/authority/AUTH-001/scenario.json",
        root / "schemas/scenario.schema.json",
    )
    record = Runner(seed_oracle_registry()).run(
        scenario,
        ReferenceAdapter(mode="guarded_pass", root=root),
    )
    if record.evidence is None:
        raise RuntimeError("reference run did not produce evidence")

    serialized = record.evidence.to_json()
    restored = EvidenceBundle.from_json(serialized)
    rescored = rescore(scenario, restored, seed_oracle_registry())
    if rescored != record.result:
        raise RuntimeError("offline rescore differs from the original result")

    target = output_path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(serialized + "\n", encoding="utf-8")
    temporary.replace(target)
    return {
        "scenario": f"{scenario.scenario_id}@{scenario.version}",
        "classification": record.result.classification.value,
        "functional": record.result.functional.value,
        "control": record.result.control.value,
        "offline_rescore_equal": True,
        "evidence_path": str(target),
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run and offline-rescore deterministic AUTH-001 reference evidence"
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    print(json.dumps(run_reference_demo(parsed.source_root, parsed.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
