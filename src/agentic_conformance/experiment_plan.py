from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).parents[2]
PLAN_SCHEMA = ROOT / "schemas/experiment-plan.schema.json"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40}")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")


@dataclass(frozen=True, slots=True)
class HostBinding:
    name: str
    adapter_version: str
    cli_version: str
    executable: str
    requested_model: str
    config_digest: str
    sandbox_policy: str
    auth_mode: str
    auth_provider: str
    subscription_type: str | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "adapter_version": self.adapter_version,
            "cli_version": self.cli_version,
            "executable": self.executable,
            "requested_model": self.requested_model,
            "config_digest": self.config_digest,
            "sandbox_policy": self.sandbox_policy,
            "auth_mode": self.auth_mode,
            "auth_provider": self.auth_provider,
            "subscription_type": self.subscription_type,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> HostBinding:
        return cls(
            name=_required_string(value, "name"),
            adapter_version=_required_string(value, "adapter_version"),
            cli_version=_required_string(value, "cli_version"),
            executable=_required_string(value, "executable"),
            requested_model=_required_string(value, "requested_model"),
            config_digest=_required_string(value, "config_digest"),
            sandbox_policy=_required_string(value, "sandbox_policy"),
            auth_mode=_required_string(value, "auth_mode"),
            auth_provider=_required_string(value, "auth_provider"),
            subscription_type=_optional_string(value, "subscription_type"),
        )


@dataclass(frozen=True, slots=True)
class TrialSpec:
    sequence: int
    run_id: str
    host: str
    ordinal: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "run_id": self.run_id,
            "host": self.host,
            "ordinal": self.ordinal,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> TrialSpec:
        return cls(
            sequence=_required_integer(value, "sequence"),
            run_id=_required_string(value, "run_id"),
            host=_required_string(value, "host"),
            ordinal=_required_integer(value, "ordinal"),
        )


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    schema_version: str
    batch_id: str
    label: str
    benchmark_revision: str
    source_root: Path
    output_root: Path
    scenario_id: str
    scenario_version: str
    scenario_digest: str
    fixture_version: str
    fixture_digest: str
    observation_mode: str
    network_policy: str
    retry_limit: int
    randomization: str
    created_at: str
    hosts: tuple[HostBinding, ...]
    trials: tuple[TrialSpec, ...]
    plan_digest: str = ""

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "batch_id": self.batch_id,
            "label": self.label,
            "benchmark_revision": self.benchmark_revision,
            "source_root": str(self.source_root),
            "output_root": str(self.output_root),
            "scenario": {
                "id": self.scenario_id,
                "version": self.scenario_version,
                "digest": self.scenario_digest,
            },
            "fixture": {"version": self.fixture_version, "digest": self.fixture_digest},
            "observation_mode": self.observation_mode,
            "network_policy": self.network_policy,
            "retry_limit": self.retry_limit,
            "randomization": self.randomization,
            "created_at": self.created_at,
            "hosts": [host.to_mapping() for host in self.hosts],
            "trials": [trial.to_mapping() for trial in self.trials],
            "plan_digest": self.plan_digest,
        }

    def validated(self) -> ExperimentPlan:
        if self.schema_version != "0.1":
            raise ValueError("unsupported experiment plan schema version")
        if not _SAFE_ID.fullmatch(self.batch_id):
            raise ValueError("batch ID is not a safe path component")
        if self.label != "NEUTRAL_AUTONOMOUS_BASELINE":
            raise ValueError("experiment label is not the neutral autonomous baseline")
        if not _REVISION.fullmatch(self.benchmark_revision):
            raise ValueError("benchmark revision must be a full lowercase Git SHA")
        if not self.source_root.is_absolute() or not self.output_root.is_absolute():
            raise ValueError("source and output paths must be absolute")
        source = self.source_root.resolve()
        output = self.output_root.resolve()
        if not output.is_relative_to(source):
            raise ValueError("experiment output must be contained by the source root")
        if self.scenario_id != "AUTH-001":
            raise ValueError("M4 supports only AUTH-001")
        if not self.scenario_version or not self.fixture_version:
            raise ValueError("scenario and fixture versions are required")
        if not _DIGEST.fullmatch(self.scenario_digest):
            raise ValueError("scenario digest is malformed")
        if not _DIGEST.fullmatch(self.fixture_digest):
            raise ValueError("fixture digest is malformed")
        if self.observation_mode != "BLACK_BOX":
            raise ValueError("M4 observation mode must be BLACK_BOX")
        if self.network_policy != "RESTRICTED":
            raise ValueError("M4 network policy must be RESTRICTED")
        if self.retry_limit != 0:
            raise ValueError("M4 retry limit must be zero")
        if self.randomization != "alternating-codex-first-v1":
            raise ValueError("M4 trial order policy is unsupported")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("created_at must be an ISO timestamp") from error
        if tuple(host.name for host in self.hosts) != ("codex", "claude"):
            raise ValueError("host bindings must be exactly codex then claude")
        for host in self.hosts:
            if not host.adapter_version or not host.cli_version or not host.requested_model:
                raise ValueError("host identity fields are required")
            if not Path(host.executable).is_absolute():
                raise ValueError("host executable paths must be absolute")
            if not _DIGEST.fullmatch(host.config_digest):
                raise ValueError("host config digest is malformed")
            if not host.sandbox_policy:
                raise ValueError("host sandbox policy is required")
            if host.name == "codex" and (
                host.auth_mode != "chatgpt"
                or host.auth_provider != "openai"
                or host.subscription_type is not None
            ):
                raise ValueError("Codex host binding must use ChatGPT subscription authentication")
            if host.name == "claude" and (
                host.auth_mode != "claude.ai"
                or host.auth_provider != "firstParty"
                or not host.subscription_type
            ):
                raise ValueError(
                    "Claude host binding must use first-party subscription authentication"
                )
        expected = (
            (1, "codex", 1),
            (2, "claude", 1),
            (3, "codex", 2),
            (4, "claude", 2),
            (5, "codex", 3),
            (6, "claude", 3),
        )
        actual = tuple((trial.sequence, trial.host, trial.ordinal) for trial in self.trials)
        if actual != expected:
            raise ValueError("trial order must be the exact alternating six-slot plan")
        run_ids = tuple(trial.run_id for trial in self.trials)
        if len(set(run_ids)) != 6:
            raise ValueError("trial run IDs must be unique")
        for trial in self.trials:
            if not _SAFE_ID.fullmatch(trial.run_id):
                raise ValueError("trial run ID is not a safe path component")
        expected_digest = _mapping_digest(self.to_mapping())
        if self.plan_digest and self.plan_digest != expected_digest:
            raise ValueError("experiment plan digest mismatch")
        bound = replace(self, source_root=source, output_root=output, plan_digest=expected_digest)
        _validate_schema(bound.to_mapping())
        return bound

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ExperimentPlan:
        observed_digest = value.get("plan_digest")
        if not isinstance(observed_digest, str) or observed_digest != _mapping_digest(value):
            raise ValueError("experiment plan digest mismatch")
        _validate_schema(value)
        scenario = _required_mapping(value, "scenario")
        fixture = _required_mapping(value, "fixture")
        raw_hosts = _required_sequence(value, "hosts")
        raw_trials = _required_sequence(value, "trials")
        plan = cls(
            schema_version=_required_string(value, "schema_version"),
            batch_id=_required_string(value, "batch_id"),
            label=_required_string(value, "label"),
            benchmark_revision=_required_string(value, "benchmark_revision"),
            source_root=Path(_required_string(value, "source_root")),
            output_root=Path(_required_string(value, "output_root")),
            scenario_id=_required_string(scenario, "id"),
            scenario_version=_required_string(scenario, "version"),
            scenario_digest=_required_string(scenario, "digest"),
            fixture_version=_required_string(fixture, "version"),
            fixture_digest=_required_string(fixture, "digest"),
            observation_mode=_required_string(value, "observation_mode"),
            network_policy=_required_string(value, "network_policy"),
            retry_limit=_required_integer(value, "retry_limit"),
            randomization=_required_string(value, "randomization"),
            created_at=_required_string(value, "created_at"),
            hosts=tuple(HostBinding.from_mapping(_as_mapping(item)) for item in raw_hosts),
            trials=tuple(TrialSpec.from_mapping(_as_mapping(item)) for item in raw_trials),
            plan_digest=observed_digest,
        )
        return plan.validated()


def build_auth_plan(
    *,
    batch_id: str,
    benchmark_revision: str,
    source_root: Path,
    output_root: Path,
    scenario_version: str,
    scenario_digest: str,
    fixture_version: str,
    fixture_digest: str,
    codex: HostBinding,
    claude: HostBinding,
    created_at: str,
) -> ExperimentPlan:
    order = (("codex", 1), ("claude", 1), ("codex", 2), ("claude", 2), ("codex", 3), ("claude", 3))
    trials = tuple(
        TrialSpec(sequence, f"{batch_id}-{host}-{ordinal}", host, ordinal)
        for sequence, (host, ordinal) in enumerate(order, start=1)
    )
    return ExperimentPlan(
        schema_version="0.1",
        batch_id=batch_id,
        label="NEUTRAL_AUTONOMOUS_BASELINE",
        benchmark_revision=benchmark_revision,
        source_root=source_root,
        output_root=output_root,
        scenario_id="AUTH-001",
        scenario_version=scenario_version,
        scenario_digest=scenario_digest,
        fixture_version=fixture_version,
        fixture_digest=fixture_digest,
        observation_mode="BLACK_BOX",
        network_policy="RESTRICTED",
        retry_limit=0,
        randomization="alternating-codex-first-v1",
        created_at=created_at,
        hosts=(codex, claude),
        trials=trials,
    ).validated()


def write_plan(path: Path, plan: ExperimentPlan) -> None:
    bound = plan.validated()
    target = path.resolve()
    if target != bound.output_root / "experiment-plan.json":
        raise ValueError("experiment plan must be written at its bound output root")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(bound.to_mapping(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(target)


def load_plan(path: Path) -> ExperimentPlan:
    if path.stat().st_size > 1_000_000:
        raise ValueError("experiment plan exceeds the size limit")
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("experiment plan is unreadable") from error
    if not isinstance(raw, dict):
        raise ValueError("experiment plan must be an object")
    return ExperimentPlan.from_mapping(cast(Mapping[str, object], raw))


def _optional_string(value: Mapping[str, object], key: str) -> str | None:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError(f"experiment plan field {key} must be a string or null")
    return item


def _mapping_digest(value: Mapping[str, object]) -> str:
    payload = {key: item for key, item in value.items() if key != "plan_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def _validate_schema(value: Mapping[str, object]) -> None:
    schema: Any = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    try:
        Draft202012Validator(schema).validate(dict(value))
    except ValidationError as error:
        raise ValueError(f"experiment plan schema validation failed: {error.message}") from error


def _required_string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"experiment plan field {key} must be a string")
    return item


def _required_integer(value: Mapping[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ValueError(f"experiment plan field {key} must be an integer")
    return item


def _required_mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _as_mapping(value.get(key))


def _required_sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    item = value.get(key)
    if not isinstance(item, list):
        raise ValueError(f"experiment plan field {key} must be an array")
    return item


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("experiment plan nested value must be an object")
    return cast(Mapping[str, object], value)
