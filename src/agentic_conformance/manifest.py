from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agentic_conformance.adapters.base import Adapter
from agentic_conformance.runner import RunRecord, scenario_digest
from agentic_conformance.scenario import Scenario


@dataclass(frozen=True, slots=True)
class ManifestMetadata:
    run_id: str
    stack_name: str
    stack_version: str | None
    stack_config_digest: str
    model_identifier: str | None
    fixture_version: str
    initial_git_sha: str | None
    task_digest: str
    environment: Mapping[str, str | None]
    network_policy: str
    started_at: str
    ended_at: str


def build_run_manifest(
    record: RunRecord,
    scenario: Scenario,
    adapter: Adapter,
    metadata: ManifestMetadata,
) -> dict[str, Any]:
    evidence = []
    if record.evidence is not None:
        evidence = [
            {
                "id": artifact.artifact_id,
                "level": artifact.level.value,
                "digest": artifact.digest,
                "path": None,
            }
            for artifact in record.evidence.artifacts
        ]

    limitations = list(record.result.limitations)
    if record.cleanup_error is not None:
        limitations.append(f"cleanup error: {record.cleanup_error}")

    return {
        "schema_version": "0.1",
        "run_id": metadata.run_id,
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
        "evidence": evidence,
        "result": record.result.to_mapping(),
        "limitations": limitations,
    }
