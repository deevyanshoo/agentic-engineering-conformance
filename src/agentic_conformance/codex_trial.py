from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from agentic_conformance.adapters.codex import (
    CodexAdapter,
    CodexRunDescription,
)
from agentic_conformance.adapters.codex_fixture import AUTH_PROMPT
from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.manifest import ManifestMetadata, build_run_manifest
from agentic_conformance.result import RunResult
from agentic_conformance.runner import Runner, rescore
from agentic_conformance.scenario import load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry

ROOT = Path(__file__).parents[2]


@dataclass(frozen=True, slots=True)
class TrialArtifacts:
    run_id: str
    output_directory: Path
    evidence_path: Path
    manifest_path: Path
    raw_jsonl_path: Path
    result: RunResult
    rescored: RunResult


def run_auth_trial(output_root: Path, adapter: CodexAdapter) -> TrialArtifacts:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    oracles = seed_oracle_registry()
    record = Runner(oracles).run(scenario, adapter)
    if record.evidence is None:
        detail = record.adapter_error or record.result.classification.value
        raise RuntimeError(f"Codex trial produced no rescorable evidence: {detail}")
    observation = adapter.last_observation
    if observation is None:
        raise RuntimeError("Codex trial completed without an observation record")

    run_id = f"auth-001-codex-{_compact_now()}-{uuid.uuid4().hex[:8]}"
    output_directory = output_root / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    staging = output_root / f".{run_id}.staging-{uuid.uuid4().hex[:8]}"
    staging.mkdir(exist_ok=False)
    staged_evidence = staging / "evidence.json"
    staged_manifest = staging / "run.json"
    staged_raw_jsonl = staging / "codex.jsonl"
    try:
        stored_evidence = record.evidence.to_json()
        _atomic_write(staged_evidence, stored_evidence + "\n")
        _atomic_write(staged_raw_jsonl, observation.process.stdout)
        reloaded = EvidenceBundle.from_json(staged_evidence.read_text(encoding="utf-8"))
        rescored = rescore(scenario, reloaded, oracles)
        if rescored != record.result:
            raise RuntimeError("stored-evidence rescore differs from initial score")

        description = observation.description
        metadata = ManifestMetadata(
            run_id=run_id,
            stack_name="OpenAI Codex CLI",
            stack_version=description.cli_version,
            stack_config_digest=_config_digest(description),
            model_identifier=description.model,
            fixture_version=scenario.version,
            initial_git_sha=observation.initial_head,
            task_digest=_digest(AUTH_PROMPT),
            environment={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "implementation": platform.python_implementation(),
            },
            network_policy="RESTRICTED",
            started_at=observation.process.started_at,
            ended_at=observation.process.ended_at,
        )
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
    evidence_path = output_directory / "evidence.json"
    manifest_path = output_directory / "run.json"
    raw_jsonl_path = output_directory / "codex.jsonl"
    return TrialArtifacts(
        run_id,
        output_directory,
        evidence_path,
        manifest_path,
        raw_jsonl_path,
        record.result,
        rescored,
    )


def _print_preflight(description: CodexRunDescription) -> None:
    value = {
        "codex_cli_version": description.cli_version,
        "model": description.model,
        "reasoning_effort": description.reasoning_effort,
        "service_tier": description.service_tier,
        "invocation": list(description.command),
        "workspace": str(description.workspace),
        "sandbox": description.sandbox,
        "target_shell_network": description.shell_network,
        "user_config_ignored": description.user_config_ignored,
        "repository_rules_ignored": description.repository_rules_ignored,
        "contamination_limitation": (
            "User-global AGENTS.md may still be inherited; authentication secrets are not copied."
        ),
        "network_limitation": "Codex host API/auth network remains necessary.",
    }
    print("CODEX_LIVE_PREFLIGHT=" + json.dumps(value, sort_keys=True), flush=True)


def _config_digest(description: CodexRunDescription) -> str:
    value = {
        "model": description.model,
        "reasoning_effort": description.reasoning_effort,
        "service_tier": description.service_tier,
        "sandbox": description.sandbox,
        "shell_network": description.shell_network,
        "user_config_ignored": description.user_config_ignored,
        "repository_rules_ignored": description.repository_rules_ignored,
    }
    return _digest(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _compact_now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _validate_schema(value: dict[str, Any], path: Path) -> None:
    schema: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def _atomic_write(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one live Codex AUTH-001 trial")
    parser.add_argument("--output-root", type=Path, default=Path("reports/runs"))
    parsed = parser.parse_args(arguments)
    adapter = CodexAdapter(before_execute=_print_preflight)
    artifacts = run_auth_trial(parsed.output_root, adapter)
    print(
        json.dumps(
            {
                "run_id": artifacts.run_id,
                "classification": artifacts.result.classification.value,
                "functional": artifacts.result.functional.value,
                "control": artifacts.result.control.value,
                "rescored_equal": artifacts.result == artifacts.rescored,
                "output_directory": str(artifacts.output_directory),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
