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
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.manifest import ManifestMetadata, build_run_manifest
from agentic_conformance.oracle import OracleRegistry
from agentic_conformance.result import RunResult
from agentic_conformance.runner import RunRecord, rescore
from agentic_conformance.scenario import Scenario

ROOT = Path(__file__).parents[2]


@dataclass(frozen=True, slots=True)
class PersistedTrial:
    run_id: str
    output_directory: Path
    evidence_path: Path
    manifest_path: Path
    raw_diagnostic_path: Path
    result: RunResult
    rescored: RunResult


def persist_trial(
    *,
    output_root: Path,
    run_id: str,
    record: RunRecord,
    scenario: Scenario,
    adapter: Adapter,
    metadata: ManifestMetadata,
    oracles: OracleRegistry,
    raw_diagnostic_name: str,
    raw_diagnostic: str,
    additional_diagnostics: Mapping[str, str] | None = None,
) -> PersistedTrial:
    if record.evidence is None:
        raise ValueError("a persisted trial requires rescorable evidence")
    if (
        not run_id
        or Path(run_id).name != run_id
        or not raw_diagnostic_name
        or Path(raw_diagnostic_name).name != raw_diagnostic_name
    ):
        raise ValueError("trial output names must be single path components")

    diagnostics = dict(additional_diagnostics or {})
    reserved = {"evidence.json", "run.json", raw_diagnostic_name}
    if any(not name or Path(name).name != name or name in reserved for name in diagnostics):
        raise ValueError("additional diagnostic names must be unique safe path components")

    output_directory = output_root / run_id
    if output_directory.exists():
        raise FileExistsError(f"trial output already exists: {run_id}")
    output_root.mkdir(parents=True, exist_ok=True)
    staging = output_root / f".{run_id}.staging-{uuid.uuid4().hex[:8]}"
    staging.mkdir(exist_ok=False)
    staged_evidence = staging / "evidence.json"
    staged_manifest = staging / "run.json"
    staged_raw = staging / raw_diagnostic_name

    try:
        _atomic_write(staged_evidence, record.evidence.to_json() + "\n")
        _atomic_write(staged_raw, raw_diagnostic)
        for name, value in diagnostics.items():
            _atomic_write(staging / name, value)
        reloaded = EvidenceBundle.from_json(staged_evidence.read_text(encoding="utf-8"))
        rescored = rescore(scenario, reloaded, oracles)
        if rescored != record.result:
            raise RuntimeError("stored-evidence rescore differs from initial score")

        manifest = build_run_manifest(record, scenario, adapter, metadata)
        for reference in manifest["evidence"]:
            reference["path"] = "evidence.json"
        _validate_schema(manifest, ROOT / "schemas/run.schema.json")
        _validate_schema(record.result.to_mapping(), ROOT / "schemas/result.schema.json")
        _atomic_write(staged_manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        staging.replace(output_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return PersistedTrial(
        run_id=run_id,
        output_directory=output_directory,
        evidence_path=output_directory / "evidence.json",
        manifest_path=output_directory / "run.json",
        raw_diagnostic_path=output_directory / raw_diagnostic_name,
        result=record.result,
        rescored=rescored,
    )


def _validate_schema(value: dict[str, Any], path: Path) -> None:
    schema: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def _atomic_write(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)
