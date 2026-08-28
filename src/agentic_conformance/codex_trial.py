from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentic_conformance.adapters.auth_fixture import (
    AuthTreatment,
    auth_prompt,
)
from agentic_conformance.adapters.codex import CodexAdapter, CodexRunDescription
from agentic_conformance.calibration_persistence import (
    PersistedCalibration,
    persist_calibration,
)
from agentic_conformance.manifest import ManifestMetadata
from agentic_conformance.result import RunResult
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import Scenario, load_scenario
from agentic_conformance.seed_oracles import seed_oracle_registry
from agentic_conformance.trial_persistence import persist_trial

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


def run_auth_trial(
    output_root: Path,
    adapter: CodexAdapter,
    *,
    run_id: str | None = None,
    scenario_version: str = "1.0.0",
    additional_diagnostics: (Mapping[str, str] | Callable[[], Mapping[str, str]] | None) = None,
) -> TrialArtifacts:
    if adapter.treatment is not AuthTreatment.AUTH_CONFLICT:
        raise ValueError("AUTH conformance trial requires the conflict treatment")
    scenario = _load_auth_scenario(scenario_version)
    oracles = seed_oracle_registry()
    record = Runner(oracles).run(scenario, adapter)
    if record.evidence is None:
        detail = record.adapter_error or record.result.classification.value
        raise RuntimeError(f"Codex trial produced no rescorable evidence: {detail}")
    observation = adapter.last_observation
    if observation is None:
        raise RuntimeError("Codex trial completed without an observation record")

    actual_run_id = run_id or f"auth-001-codex-{_compact_now()}-{uuid.uuid4().hex[:8]}"
    description = observation.description
    metadata = ManifestMetadata(
        run_id=actual_run_id,
        stack_name="OpenAI Codex CLI",
        stack_version=description.cli_version,
        stack_config_digest=codex_config_digest(description),
        model_identifier=description.model,
        fixture_version=_fixture_version(scenario),
        initial_git_sha=observation.initial_head,
        task_digest=_digest(auth_prompt(adapter.treatment)),
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "implementation": platform.python_implementation(),
        },
        network_policy="RESTRICTED",
        started_at=observation.process.started_at,
        ended_at=observation.process.ended_at,
    )
    persisted = persist_trial(
        output_root=output_root,
        run_id=actual_run_id,
        record=record,
        scenario=scenario,
        adapter=adapter,
        metadata=metadata,
        oracles=oracles,
        raw_diagnostic_name="codex.jsonl",
        raw_diagnostic=observation.process.stdout,
        additional_diagnostics=(
            additional_diagnostics() if callable(additional_diagnostics) else additional_diagnostics
        ),
    )
    return TrialArtifacts(
        run_id=persisted.run_id,
        output_directory=persisted.output_directory,
        evidence_path=persisted.evidence_path,
        manifest_path=persisted.manifest_path,
        raw_jsonl_path=persisted.raw_diagnostic_path,
        result=persisted.result,
        rescored=persisted.rescored,
    )


def run_auth_calibration_trial(
    output_root: Path,
    adapter: CodexAdapter,
    *,
    run_id: str | None = None,
    additional_diagnostics: (Mapping[str, str] | Callable[[], Mapping[str, str]] | None) = None,
) -> PersistedCalibration:
    if adapter.treatment is not AuthTreatment.CALIBRATION:
        raise ValueError("calibration trial requires the no-conflict treatment")
    scenario = _load_auth_scenario("2.0.0")
    record = Runner(seed_oracle_registry()).run(scenario, adapter)
    if record.evidence is None:
        detail = record.adapter_error or record.result.classification.value
        raise RuntimeError(f"Codex calibration produced no rescorable evidence: {detail}")
    observation = adapter.last_observation
    if observation is None:
        raise RuntimeError("Codex calibration completed without an observation record")
    actual_run_id = run_id or f"auth-cal-codex-{_compact_now()}-{uuid.uuid4().hex[:8]}"
    description = observation.description
    metadata = ManifestMetadata(
        run_id=actual_run_id,
        stack_name="OpenAI Codex CLI",
        stack_version=description.cli_version,
        stack_config_digest=codex_config_digest(description),
        model_identifier=description.model,
        fixture_version=_fixture_version(scenario),
        initial_git_sha=observation.initial_head,
        task_digest=_digest(auth_prompt(adapter.treatment)),
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "implementation": platform.python_implementation(),
        },
        network_policy="RESTRICTED",
        started_at=observation.process.started_at,
        ended_at=observation.process.ended_at,
    )
    return persist_calibration(
        output_root=output_root,
        run_id=actual_run_id,
        record=record,
        scenario=scenario,
        adapter=adapter,
        metadata=metadata,
        raw_diagnostic_name="codex.jsonl",
        raw_diagnostic=observation.process.stdout,
        additional_diagnostics=(
            additional_diagnostics() if callable(additional_diagnostics) else additional_diagnostics
        ),
    )


def _load_auth_scenario(version: str) -> Scenario:
    filename = {"1.0.0": "scenario.json", "2.0.0": "scenario-v2.json"}.get(version)
    if filename is None:
        raise ValueError("unsupported AUTH-001 scenario version")
    return load_scenario(
        ROOT / "scenarios/authority/AUTH-001" / filename,
        ROOT / "schemas/scenario.schema.json",
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


def codex_config_digest(description: CodexRunDescription) -> str:
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


def _fixture_version(scenario: Scenario) -> str:
    value = scenario.ground_truth.get("fixture_version")
    if not isinstance(value, str):
        raise RuntimeError("AUTH-001 fixture version is unavailable")
    return value


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _compact_now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


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
