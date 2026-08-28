from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentic_conformance.adapters.auth_fixture import AUTH_PROMPT
from agentic_conformance.adapters.claude import ClaudeAdapter, ClaudeRunDescription
from agentic_conformance.manifest import ManifestMetadata
from agentic_conformance.result import RunResult
from agentic_conformance.runner import Runner
from agentic_conformance.scenario import load_scenario
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


def run_auth_trial(output_root: Path, adapter: ClaudeAdapter) -> TrialArtifacts:
    scenario = load_scenario(
        ROOT / "scenarios/authority/AUTH-001/scenario.json",
        ROOT / "schemas/scenario.schema.json",
    )
    oracles = seed_oracle_registry()
    record = Runner(oracles).run(scenario, adapter)
    if record.evidence is None:
        detail = record.adapter_error or record.result.classification.value
        raise RuntimeError(f"Claude trial produced no rescorable evidence: {detail}")
    observation = adapter.last_observation
    if observation is None:
        raise RuntimeError("Claude trial completed without an observation record")

    fixture_version = scenario.ground_truth.get("fixture_version")
    if not isinstance(fixture_version, str):
        raise RuntimeError("AUTH-001 fixture version is unavailable")

    run_id = f"auth-001-claude-{_compact_now()}-{uuid.uuid4().hex[:8]}"
    description = observation.description
    metadata = ManifestMetadata(
        run_id=run_id,
        stack_name="Anthropic Claude Code",
        stack_version=description.cli_version,
        stack_config_digest=_config_digest(description),
        model_identifier=observation.observed_model or description.requested_model,
        fixture_version=fixture_version,
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
    persisted = persist_trial(
        output_root=output_root,
        run_id=run_id,
        record=record,
        scenario=scenario,
        adapter=adapter,
        metadata=metadata,
        oracles=oracles,
        raw_diagnostic_name="claude.jsonl",
        raw_diagnostic=observation.process.stdout,
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


def _print_preflight(description: ClaudeRunDescription) -> None:
    value = {
        "claude_cli_version": description.cli_version,
        "requested_model": description.requested_model,
        "invocation": list(description.command),
        "workspace": str(description.workspace),
        "output_format": description.output_format,
        "permission_mode": description.permission_mode,
        "tools": list(description.tools),
        "safe_mode": description.safe_mode,
        "session_persistence": description.session_persistence,
        "target_shell_available": description.target_shell_available,
        "target_web_available": description.target_web_available,
        "user_project_config_disabled": description.user_project_config_disabled,
        "managed_policy_observable": description.managed_policy_observable,
        "contamination_limitation": (
            "Safe mode disables user/project customizations, but administrator-managed policy "
            "may still apply; authentication credentials are not copied."
        ),
        "network_limitation": (
            "Claude host authentication/model traffic requires network; the target tool set "
            "contains no shell or web tool."
        ),
    }
    print("CLAUDE_LIVE_PREFLIGHT=" + json.dumps(value, sort_keys=True), flush=True)


def _config_digest(description: ClaudeRunDescription) -> str:
    value = {
        "requested_model": description.requested_model,
        "output_format": description.output_format,
        "permission_mode": description.permission_mode,
        "tools": list(description.tools),
        "safe_mode": description.safe_mode,
        "session_persistence": description.session_persistence,
        "target_shell_available": description.target_shell_available,
        "target_web_available": description.target_web_available,
        "user_project_config_disabled": description.user_project_config_disabled,
        "managed_policy_observable": description.managed_policy_observable,
    }
    return _digest(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _compact_now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one live Claude AUTH-001 trial")
    parser.add_argument("--output-root", type=Path, default=Path("reports/runs"))
    parsed = parser.parse_args(arguments)
    adapter = ClaudeAdapter(before_execute=_print_preflight)
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
