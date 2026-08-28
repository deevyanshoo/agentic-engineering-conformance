from __future__ import annotations

import json
from pathlib import Path

from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.calibration import CalibrationClassification
from agentic_conformance.calibration_persistence import persist_calibration
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.manifest import ManifestMetadata
from agentic_conformance.result import ControlResponse, Outcome, RunClassification, RunResult
from agentic_conformance.runner import RunRecord, scenario_digest
from agentic_conformance.scenario import Scenario, load_scenario

ROOT = Path(__file__).parents[2]


class FakeAdapter(Adapter):
    name = "fake-host"
    version = "1.0"

    def probe(self) -> frozenset[str]:
        raise NotImplementedError

    def prepare(self, scenario: Scenario) -> PreparedRun:
        raise NotImplementedError

    def execute(self, prepared: PreparedRun) -> None:
        raise NotImplementedError

    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        raise NotImplementedError

    def cleanup(self, prepared: PreparedRun) -> None:
        raise NotImplementedError


def test_persists_separate_calibration_result_and_offline_rescore(tmp_path: Path) -> None:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario-v2.json",
        ROOT / "schemas/scenario.schema.json",
    )
    digest = scenario_digest(scenario)
    evidence = EvidenceBundle.create(
        scenario.scenario_id,
        scenario.version,
        digest,
        scenario.ground_truth,
        (
            EvidenceArtifact.create(
                "final",
                EvidenceLevel.E1,
                "final_behavior",
                "ADAPTER_OBSERVER",
                {"behavior": "B"},
                digest,
            ),
        ),
    )
    transient = RunResult(
        Outcome.PASS,
        Outcome.PASS,
        RunClassification.BEHAVIORAL_PASS,
        ControlResponse.BEHAVIOR_ONLY,
        ("transient conformance score",),
        (),
    )
    record = RunRecord(transient, evidence, True)
    metadata = ManifestMetadata(
        "calibration-run",
        "Synthetic host",
        "1.0",
        "sha256:" + "a" * 64,
        "model",
        "1.0.0",
        "b" * 40,
        "sha256:" + "c" * 64,
        {"python": "test"},
        "RESTRICTED",
        "2026-08-29T12:00:00Z",
        "2026-08-29T12:00:01Z",
    )

    persisted = persist_calibration(
        output_root=tmp_path,
        run_id="calibration-run",
        record=record,
        scenario=scenario,
        adapter=FakeAdapter(),
        metadata=metadata,
        raw_diagnostic_name="host.jsonl",
        raw_diagnostic="{}\n",
    )

    assert persisted.result.classification is CalibrationClassification.CALIBRATION_PASS
    assert persisted.rescored == persisted.result
    manifest = json.loads(persisted.manifest_path.read_text(encoding="utf-8"))
    assert manifest["assessment"] == "AUTH_CALIBRATION"
    assert manifest["treatment"] == "CALIBRATION"
    assert manifest["result"]["outcome"] == "CALIBRATION_PASS"
    assert "classification" not in manifest["result"]
    assert "control" not in manifest["result"]
    assert (persisted.output_directory / "evidence.json").exists()
    assert not (tmp_path / ".calibration-run.staging").exists()


def test_cleanup_failure_is_persisted_and_rescored_as_invalid(tmp_path: Path) -> None:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario-v2.json",
        ROOT / "schemas/scenario.schema.json",
    )
    digest = scenario_digest(scenario)
    evidence = EvidenceBundle.create(
        scenario.scenario_id,
        scenario.version,
        digest,
        scenario.ground_truth,
        (
            EvidenceArtifact.create(
                "final",
                EvidenceLevel.E1,
                "final_behavior",
                "ADAPTER_OBSERVER",
                {"behavior": "B"},
                digest,
            ),
        ),
    )
    transient = RunResult(
        Outcome.PASS,
        Outcome.PASS,
        RunClassification.BEHAVIORAL_PASS,
        ControlResponse.BEHAVIOR_ONLY,
        ("transient conformance score",),
        (),
    )
    record = RunRecord(transient, evidence, True, cleanup_error="fixture remained")
    metadata = ManifestMetadata(
        "cleanup-failure",
        "Synthetic host",
        "1.0",
        "sha256:" + "a" * 64,
        "model",
        "1.0.0",
        "b" * 40,
        "sha256:" + "c" * 64,
        {"python": "test"},
        "RESTRICTED",
        "2026-08-29T12:00:00Z",
        "2026-08-29T12:00:01Z",
    )

    persisted = persist_calibration(
        output_root=tmp_path,
        run_id="cleanup-failure",
        record=record,
        scenario=scenario,
        adapter=FakeAdapter(),
        metadata=metadata,
        raw_diagnostic_name="host.jsonl",
        raw_diagnostic="{}\n",
    )

    assert persisted.result.classification is CalibrationClassification.CALIBRATION_INVALID
    assert persisted.rescored == persisted.result
    reloaded = EvidenceBundle.from_json(persisted.evidence_path.read_text(encoding="utf-8"))
    lifecycle = reloaded.artifacts_of_kind("calibration_lifecycle")
    assert len(lifecycle) == 1
    assert lifecycle[0].data == {"cleanup_succeeded": False}
    manifest = json.loads(persisted.manifest_path.read_text(encoding="utf-8"))
    assert manifest["result"]["outcome"] == "CALIBRATION_INVALID"
