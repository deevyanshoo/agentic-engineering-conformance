import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from agentic_conformance.adapters.reference import ReferenceAdapter
from agentic_conformance.manifest import ManifestMetadata, build_run_manifest
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


def test_actual_run_record_builds_schema_valid_manifest() -> None:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    adapter = ReferenceAdapter("guarded_pass")
    record = Runner(seed_oracle_registry()).run(scenario, adapter)
    metadata = ManifestMetadata(
        run_id="run-auth-001",
        stack_name="reference-stack",
        stack_version="1.0.0",
        stack_config_digest="sha256:stack-config",
        model_identifier=None,
        fixture_version="1.0.0",
        initial_git_sha=None,
        task_digest="sha256:task-payload",
        environment={"python": "3.13.3", "platform": "win32"},
        network_policy="DENY",
        started_at="2026-08-27T00:00:00Z",
        ended_at="2026-08-27T00:00:01Z",
    )

    manifest = build_run_manifest(record, scenario, adapter, metadata)

    with (ROOT / "schemas/run.schema.json").open(encoding="utf-8") as handle:
        schema: dict[str, Any] = json.load(handle)
    Draft202012Validator(schema).validate(manifest)
    assert manifest["result"]["functional"] == "PASS"
    assert manifest["result"]["control"] == "PASS"
    assert manifest["evidence"][0]["level"] in {"E0", "E1", "E2", "E3", "E4"}


def test_unknown_host_identity_is_represented_honestly() -> None:
    metadata = ManifestMetadata(
        run_id="run-unknown",
        stack_name="unknown-stack",
        stack_version=None,
        stack_config_digest="sha256:unknown-config",
        model_identifier=None,
        fixture_version="1.0.0",
        initial_git_sha=None,
        task_digest="sha256:task",
        environment={"host": None},
        network_policy="DENY",
        started_at="2026-08-27T00:00:00Z",
        ended_at="2026-08-27T00:00:00Z",
    )
    assert metadata.stack_version is None
    assert metadata.model_identifier is None
