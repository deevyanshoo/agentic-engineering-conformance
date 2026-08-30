from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from agentic_conformance.adapters.base import Adapter
from agentic_conformance.calibration import (
    CalibrationResult,
    rescore_auth_calibration,
)
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.manifest import ManifestMetadata
from agentic_conformance.runner import RunRecord, scenario_digest
from agentic_conformance.scenario import Scenario

ROOT = Path(__file__).parents[2]


@dataclass(frozen=True, slots=True)
class PersistedCalibration:
    run_id: str
    output_directory: Path
    evidence_path: Path
    manifest_path: Path
    raw_diagnostic_path: Path
    result: CalibrationResult
    rescored: CalibrationResult


def persist_calibration(
    *,
    output_root: Path,
    run_id: str,
    record: RunRecord,
    scenario: Scenario,
    adapter: Adapter,
    metadata: ManifestMetadata,
    raw_diagnostic_name: str,
    raw_diagnostic: str,
    additional_diagnostics: Mapping[str, str] | None = None,
) -> PersistedCalibration:
    if record.evidence is None:
        raise ValueError("a persisted calibration requires rescorable evidence")
    if (
        not run_id
        or Path(run_id).name != run_id
        or not raw_diagnostic_name
        or Path(raw_diagnostic_name).name != raw_diagnostic_name
    ):
        raise ValueError("calibration output names must be single path components")
    if record.evidence.artifacts_of_kind("calibration_lifecycle"):
        raise ValueError("adapter evidence cannot supply benchmark lifecycle validity")
    lifecycle = EvidenceArtifact.create(
        f"{run_id}-calibration-lifecycle",
        EvidenceLevel.E1,
        "calibration_lifecycle",
        "BENCHMARK_RUNNER",
        {"cleanup_succeeded": record.cleanup_error is None},
        scenario_digest(scenario),
    )
    persisted_evidence = EvidenceBundle.create(
        record.evidence.scenario_id,
        record.evidence.scenario_version,
        record.evidence.scenario_digest,
        record.evidence.ground_truth,
        (*record.evidence.artifacts, lifecycle),
        record.evidence.limitations,
    )
    diagnostics = dict(additional_diagnostics or {})
    reserved = {"evidence.json", "calibration.json", raw_diagnostic_name}
    if any(not name or Path(name).name != name or name in reserved for name in diagnostics):
        raise ValueError("additional diagnostic names must be unique safe path components")

    output_directory = output_root / run_id
    if output_directory.exists():
        raise FileExistsError(f"calibration output already exists: {run_id}")
    output_root.mkdir(parents=True, exist_ok=True)
    staging = output_root / f".{run_id}.staging-{uuid.uuid4().hex[:8]}"
    staging.mkdir(exist_ok=False)
    staged_evidence = staging / "evidence.json"
    staged_manifest = staging / "calibration.json"
    staged_raw = staging / raw_diagnostic_name
    try:
        _atomic_write(staged_evidence, persisted_evidence.to_json() + "\n")
        _atomic_write(staged_raw, raw_diagnostic)
        for name, value in diagnostics.items():
            _atomic_write(staging / name, value)
        reloaded = EvidenceBundle.from_json(staged_evidence.read_text(encoding="utf-8"))
        initial = rescore_auth_calibration(scenario, persisted_evidence)
        rescored = rescore_auth_calibration(scenario, reloaded)
        if rescored != initial:
            raise RuntimeError("stored-evidence calibration rescore differs from initial score")
        manifest = _manifest(record, persisted_evidence, scenario, adapter, metadata, initial)
        _validate_schema(manifest, ROOT / "schemas/calibration-run.schema.json")
        _validate_schema(initial.to_mapping(), ROOT / "schemas/calibration-result.schema.json")
        _atomic_write(staged_manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        staging.replace(output_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return PersistedCalibration(
        run_id,
        output_directory,
        output_directory / "evidence.json",
        output_directory / "calibration.json",
        output_directory / raw_diagnostic_name,
        initial,
        rescored,
    )


def _manifest(
    record: RunRecord,
    evidence: EvidenceBundle,
    scenario: Scenario,
    adapter: Adapter,
    metadata: ManifestMetadata,
    result: CalibrationResult,
) -> dict[str, Any]:
    assert record.evidence is not None
    limitations = list(result.limitations)
    if record.cleanup_error is not None:
        limitations.append(f"cleanup error: {record.cleanup_error}")
    return {
        "schema_version": "0.1",
        "run_id": metadata.run_id,
        "assessment": "AUTH_CALIBRATION",
        "treatment": "CALIBRATION",
        "scenario": {
            "id": scenario.scenario_id,
            "version": scenario.version,
            "digest": scenario_digest(scenario),
        },
        "adapter": {"name": adapter.name, "version": adapter.version},
        "stack": {
            "name": metadata.stack_name,
            "version": metadata.stack_version,
            "config_digest": metadata.stack_config_digest,
        },
        "model_identifier": metadata.model_identifier,
        "fixture_version": metadata.fixture_version,
        "initial_git_sha": metadata.initial_git_sha,
        "task_digest": metadata.task_digest,
        "environment": dict(metadata.environment),
        "network_policy": metadata.network_policy,
        "started_at": metadata.started_at,
        "ended_at": metadata.ended_at,
        "evidence": [
            {
                "id": artifact.artifact_id,
                "level": artifact.level.value,
                "digest": artifact.digest,
                "path": "evidence.json",
            }
            for artifact in evidence.artifacts
        ],
        "result": result.to_mapping(),
        "limitations": limitations,
    }


def _validate_schema(value: dict[str, Any], path: Path) -> None:
    schema: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def _atomic_write(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)
