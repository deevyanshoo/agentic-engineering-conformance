from __future__ import annotations

import hashlib
import json
import ntpath
import posixpath
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).parents[2]
PLAN_SCHEMA = ROOT / "schemas/experiment-plan.schema.json"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40}")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")


@dataclass(frozen=True, slots=True, eq=False)
class _PersistedPath:
    raw: str
    identity: PurePath

    def __fspath__(self) -> str:
        return self.raw

    def __str__(self) -> str:
        return self.raw

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _PersistedPath):
            return self.raw == other.raw
        if isinstance(other, PurePath):
            return self.raw == str(other)
        return False

    def __hash__(self) -> int:
        return hash(self.identity)


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


class TrialCondition(StrEnum):
    CALIBRATION = "CALIBRATION"
    AUTH_CONFLICT = "AUTH_CONFLICT"


@dataclass(frozen=True, slots=True)
class TrialSpec:
    sequence: int
    run_id: str
    host: str
    ordinal: int
    condition: TrialCondition | None = None

    def to_mapping(self) -> dict[str, object]:
        value: dict[str, object] = {
            "sequence": self.sequence,
            "run_id": self.run_id,
            "host": self.host,
            "ordinal": self.ordinal,
        }
        if self.condition is not None:
            value["condition"] = self.condition.value
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> TrialSpec:
        raw_condition = value.get("condition")
        condition = TrialCondition(raw_condition) if isinstance(raw_condition, str) else None
        return cls(
            sequence=_required_integer(value, "sequence"),
            run_id=_required_string(value, "run_id"),
            host=_required_string(value, "host"),
            ordinal=_required_integer(value, "ordinal"),
            condition=condition,
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
    calibration_prompt_digest: str | None = None
    auth_conflict_prompt_digest: str | None = None
    plan_digest: str = ""

    def to_mapping(self) -> dict[str, object]:
        fixture: dict[str, object] = {
            "version": self.fixture_version,
            "digest": self.fixture_digest,
        }
        if self.schema_version == "0.2":
            fixture["treatment_digests"] = {
                TrialCondition.CALIBRATION.value: self.calibration_prompt_digest,
                TrialCondition.AUTH_CONFLICT.value: self.auth_conflict_prompt_digest,
            }
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
            "fixture": fixture,
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
        if self.schema_version not in {"0.1", "0.2"}:
            raise ValueError("unsupported experiment plan schema version")
        if not _SAFE_ID.fullmatch(self.batch_id):
            raise ValueError("batch ID is not a safe path component")
        expected_label = (
            "NEUTRAL_AUTONOMOUS_BASELINE"
            if self.schema_version == "0.1"
            else "AUTH_CONSTRUCT_VALIDITY_PAIRED"
        )
        if self.label != expected_label:
            raise ValueError("experiment label does not match its schema version")
        if not _REVISION.fullmatch(self.benchmark_revision):
            raise ValueError("benchmark revision must be a full lowercase Git SHA")
        stored_source, source_identity = _validated_persisted_path(self.source_root)
        stored_output, output_identity = _validated_persisted_path(self.output_root)
        normalized_source = _normalized_persisted_path(source_identity)
        normalized_output = _normalized_persisted_path(output_identity)
        if not _same_path_flavour(
            source_identity, output_identity
        ) or not normalized_output.is_relative_to(normalized_source):
            raise ValueError("experiment output must be contained by the source root")
        if self.scenario_id != "AUTH-001":
            raise ValueError("neutral experiments support only AUTH-001")
        if not self.scenario_version or not self.fixture_version:
            raise ValueError("scenario and fixture versions are required")
        if not _DIGEST.fullmatch(self.scenario_digest):
            raise ValueError("scenario digest is malformed")
        if not _DIGEST.fullmatch(self.fixture_digest):
            raise ValueError("fixture digest is malformed")
        if self.observation_mode != "BLACK_BOX":
            raise ValueError("observation mode must be BLACK_BOX")
        if self.network_policy != "RESTRICTED":
            raise ValueError("network policy must be RESTRICTED")
        if self.retry_limit != 0:
            raise ValueError("retry limit must be zero")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("created_at must be an ISO timestamp") from error
        self._validate_hosts()
        self._validate_experiment_shape()
        expected_digest = _mapping_digest(self.to_mapping())
        if self.plan_digest and self.plan_digest != expected_digest:
            raise ValueError("experiment plan digest mismatch")
        bound = replace(
            self,
            source_root=cast(Path, stored_source),
            output_root=cast(Path, stored_output),
            plan_digest=expected_digest,
        )
        _validate_schema(bound.to_mapping())
        return bound

    def _validate_hosts(self) -> None:
        if tuple(host.name for host in self.hosts) != ("codex", "claude"):
            raise ValueError("host bindings must be exactly codex then claude")
        for host in self.hosts:
            if not host.adapter_version or not host.cli_version or not host.requested_model:
                raise ValueError("host identity fields are required")
            if _portable_absolute_path(host.executable) is None:
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

    def _validate_experiment_shape(self) -> None:
        if self.schema_version == "0.1":
            if self.randomization != "alternating-codex-first-v1":
                raise ValueError("M4 trial order policy is unsupported")
            expected: tuple[tuple[int, str, int, TrialCondition | None], ...] = (
                (1, "codex", 1, None),
                (2, "claude", 1, None),
                (3, "codex", 2, None),
                (4, "claude", 2, None),
                (5, "codex", 3, None),
                (6, "claude", 3, None),
            )
            if (
                self.calibration_prompt_digest is not None
                or self.auth_conflict_prompt_digest is not None
            ):
                raise ValueError("M4 plan cannot bind M5 treatment digests")
        else:
            if self.randomization != "paired-host-blocks-v1":
                raise ValueError("M5 trial order policy is unsupported")
            if self.scenario_version != "2.0.0":
                raise ValueError("M5 paired plan requires AUTH-001 scenario version 2.0.0")
            if not _is_digest(self.calibration_prompt_digest) or not _is_digest(
                self.auth_conflict_prompt_digest
            ):
                raise ValueError("M5 treatment digest is malformed")
            expected = tuple(
                (sequence, host, ordinal, condition)
                for sequence, (host, condition, ordinal) in enumerate(
                    (
                        ("codex", TrialCondition.CALIBRATION, 1),
                        ("codex", TrialCondition.AUTH_CONFLICT, 1),
                        ("claude", TrialCondition.CALIBRATION, 1),
                        ("claude", TrialCondition.AUTH_CONFLICT, 1),
                        ("codex", TrialCondition.CALIBRATION, 2),
                        ("codex", TrialCondition.AUTH_CONFLICT, 2),
                        ("claude", TrialCondition.CALIBRATION, 2),
                        ("claude", TrialCondition.AUTH_CONFLICT, 2),
                        ("codex", TrialCondition.CALIBRATION, 3),
                        ("codex", TrialCondition.AUTH_CONFLICT, 3),
                        ("claude", TrialCondition.CALIBRATION, 3),
                        ("claude", TrialCondition.AUTH_CONFLICT, 3),
                    ),
                    start=1,
                )
            )
        actual = tuple(
            (trial.sequence, trial.host, trial.ordinal, trial.condition) for trial in self.trials
        )
        if actual != expected:
            raise ValueError("trial order does not match the exact bound plan order")
        run_ids = tuple(trial.run_id for trial in self.trials)
        if len(set(run_ids)) != len(self.trials):
            raise ValueError("trial run IDs must be unique")
        for trial in self.trials:
            if not _SAFE_ID.fullmatch(trial.run_id):
                raise ValueError("trial run ID is not a safe path component")

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
        treatments_raw = fixture.get("treatment_digests")
        treatments = _as_mapping(treatments_raw) if treatments_raw is not None else {}
        plan = cls(
            schema_version=_required_string(value, "schema_version"),
            batch_id=_required_string(value, "batch_id"),
            label=_required_string(value, "label"),
            benchmark_revision=_required_string(value, "benchmark_revision"),
            source_root=cast(Path, _required_absolute_path(value, "source_root")),
            output_root=cast(Path, _required_absolute_path(value, "output_root")),
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
            calibration_prompt_digest=_optional_mapping_string(
                treatments, TrialCondition.CALIBRATION.value
            ),
            auth_conflict_prompt_digest=_optional_mapping_string(
                treatments, TrialCondition.AUTH_CONFLICT.value
            ),
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


def build_paired_auth_plan(
    *,
    batch_id: str,
    benchmark_revision: str,
    source_root: Path,
    output_root: Path,
    scenario_version: str,
    scenario_digest: str,
    fixture_version: str,
    fixture_base_digest: str,
    calibration_prompt_digest: str,
    auth_conflict_prompt_digest: str,
    codex: HostBinding,
    claude: HostBinding,
    created_at: str,
) -> ExperimentPlan:
    order = (
        ("codex", TrialCondition.CALIBRATION, 1),
        ("codex", TrialCondition.AUTH_CONFLICT, 1),
        ("claude", TrialCondition.CALIBRATION, 1),
        ("claude", TrialCondition.AUTH_CONFLICT, 1),
        ("codex", TrialCondition.CALIBRATION, 2),
        ("codex", TrialCondition.AUTH_CONFLICT, 2),
        ("claude", TrialCondition.CALIBRATION, 2),
        ("claude", TrialCondition.AUTH_CONFLICT, 2),
        ("codex", TrialCondition.CALIBRATION, 3),
        ("codex", TrialCondition.AUTH_CONFLICT, 3),
        ("claude", TrialCondition.CALIBRATION, 3),
        ("claude", TrialCondition.AUTH_CONFLICT, 3),
    )
    trials = tuple(
        TrialSpec(
            sequence,
            f"{batch_id}-{host}-{_condition_slug(condition)}-{ordinal}",
            host,
            ordinal,
            condition,
        )
        for sequence, (host, condition, ordinal) in enumerate(order, start=1)
    )
    return ExperimentPlan(
        schema_version="0.2",
        batch_id=batch_id,
        label="AUTH_CONSTRUCT_VALIDITY_PAIRED",
        benchmark_revision=benchmark_revision,
        source_root=source_root,
        output_root=output_root,
        scenario_id="AUTH-001",
        scenario_version=scenario_version,
        scenario_digest=scenario_digest,
        fixture_version=fixture_version,
        fixture_digest=fixture_base_digest,
        observation_mode="BLACK_BOX",
        network_policy="RESTRICTED",
        retry_limit=0,
        randomization="paired-host-blocks-v1",
        created_at=created_at,
        hosts=(codex, claude),
        trials=trials,
        calibration_prompt_digest=calibration_prompt_digest,
        auth_conflict_prompt_digest=auth_conflict_prompt_digest,
    ).validated()


def write_plan(path: Path, plan: ExperimentPlan) -> None:
    bound = bind_plan_to_local_runtime(plan)
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


def bind_plan_to_local_runtime(plan: ExperimentPlan) -> ExperimentPlan:
    """Bind portable persisted path identities to this machine before local I/O."""
    validated = plan.validated()
    _, source_identity = _validated_persisted_path(validated.source_root)
    _, output_identity = _validated_persisted_path(validated.output_root)
    host_identities = tuple(_portable_absolute_path(host.executable) for host in validated.hosts)
    if not _is_runtime_path(source_identity) or not _is_runtime_path(output_identity):
        raise ValueError("experiment paths are incompatible with the current runtime")
    if any(identity is None or not _is_runtime_path(identity) for identity in host_identities):
        raise ValueError("host executable path is incompatible with the current runtime")
    source = Path(validated.source_root)
    output = Path(validated.output_root)
    if not source.is_absolute() or not output.is_absolute():
        raise ValueError("experiment paths are incompatible with the current runtime")
    source = source.resolve()
    output = output.resolve()
    if not output.is_relative_to(source):
        raise ValueError("experiment output must be contained by the source root")
    return replace(validated, source_root=source, output_root=output)


def _validated_persisted_path(
    value: Path,
) -> tuple[Path | _PersistedPath, PurePath]:
    if isinstance(value, Path):
        if not value.is_absolute():
            raise ValueError("source and output paths must be absolute")
        return value, value
    if isinstance(value, _PersistedPath):
        return value, value.identity
    raw = str(value)
    parsed = _portable_absolute_path(raw)
    if parsed is None:
        raise ValueError("source and output paths must be absolute")
    preserved = _PersistedPath(raw, parsed)
    return preserved, parsed


def _normalized_persisted_path(value: PurePath) -> PurePath:
    if isinstance(value, PureWindowsPath):
        return PureWindowsPath(ntpath.normpath(str(value)))
    return PurePosixPath(posixpath.normpath(str(value)))


def _portable_absolute_path(value: str) -> PurePath | None:
    if not value or "\x00" in value:
        return None
    windows = PureWindowsPath(value)
    if windows.is_absolute():
        return windows
    posix = PurePosixPath(value)
    if posix.is_absolute():
        return posix
    return None


def _same_path_flavour(left: PurePath, right: PurePath) -> bool:
    return isinstance(left, PureWindowsPath) is isinstance(right, PureWindowsPath)


def _is_runtime_path(identity: PurePath) -> bool:
    runtime_is_windows = isinstance(PurePath(), PureWindowsPath)
    return isinstance(identity, PureWindowsPath) is runtime_is_windows


def _required_absolute_path(value: Mapping[str, object], key: str) -> Path | _PersistedPath:
    raw = _required_string(value, key)
    identity = _portable_absolute_path(raw)
    if identity is None:
        raise ValueError("source and output paths must be absolute")
    return _PersistedPath(raw, identity)


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


def _is_digest(value: str | None) -> bool:
    return value is not None and _DIGEST.fullmatch(value) is not None


def _condition_slug(condition: TrialCondition) -> str:
    return "cal" if condition is TrialCondition.CALIBRATION else "auth"


def _optional_mapping_string(value: Mapping[str, object], key: str) -> str | None:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError(f"experiment plan field {key} must be a string or null")
    return item
