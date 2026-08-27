from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EvidenceLevel(StrEnum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _artifact_digest(
    artifact_id: str,
    level: EvidenceLevel,
    kind: str,
    producer: str,
    data_json: str,
    subject_digest: str | None,
) -> str:
    envelope = {
        "id": artifact_id,
        "level": level.value,
        "kind": kind,
        "producer": producer,
        "data": json.loads(data_json),
        "subject_digest": subject_digest,
    }
    return _digest(_canonical_json(envelope))


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    artifact_id: str
    level: EvidenceLevel
    kind: str
    producer: str
    data_json: str
    digest: str
    subject_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            data = json.loads(self.data_json)
        except json.JSONDecodeError as exc:
            raise ValueError("evidence artifact data must be valid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("evidence artifact data must be a JSON object")
        canonical_data = _canonical_json(data)
        if canonical_data != self.data_json:
            raise ValueError("evidence artifact data must use canonical JSON")
        expected_digest = _artifact_digest(
            self.artifact_id,
            self.level,
            self.kind,
            self.producer,
            self.data_json,
            self.subject_digest,
        )
        if self.digest != expected_digest:
            raise ValueError("evidence artifact digest does not match its envelope")

    @property
    def data(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.data_json)
        return value

    @classmethod
    def create(
        cls,
        artifact_id: str,
        level: EvidenceLevel,
        kind: str,
        producer: str,
        data: Mapping[str, Any],
        subject_digest: str | None = None,
    ) -> EvidenceArtifact:
        data_json = _canonical_json(data)
        digest = _artifact_digest(artifact_id, level, kind, producer, data_json, subject_digest)
        return cls(artifact_id, level, kind, producer, data_json, digest, subject_digest)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.artifact_id,
            "level": self.level.value,
            "kind": self.kind,
            "producer": self.producer,
            "data": self.data,
            "digest": self.digest,
            "subject_digest": self.subject_digest,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> EvidenceArtifact:
        expected_fields = {
            "id",
            "level",
            "kind",
            "producer",
            "data",
            "digest",
            "subject_digest",
        }
        if set(value) != expected_fields:
            raise ValueError("stored evidence artifact fields are incompatible")
        data_json = _canonical_json(value["data"])
        level = EvidenceLevel(value["level"])
        expected_digest = _artifact_digest(
            value["id"],
            level,
            value["kind"],
            value["producer"],
            data_json,
            value.get("subject_digest"),
        )
        if value["digest"] != expected_digest:
            raise ValueError("stored evidence digest does not match its payload")
        return cls(
            artifact_id=value["id"],
            level=level,
            kind=value["kind"],
            producer=value["producer"],
            data_json=data_json,
            digest=value["digest"],
            subject_digest=value.get("subject_digest"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    scenario_id: str
    scenario_version: str
    scenario_digest: str
    ground_truth_json: str
    artifacts: tuple[EvidenceArtifact, ...]
    limitations: tuple[str, ...] = ()

    @property
    def ground_truth(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.ground_truth_json)
        return value

    @classmethod
    def create(
        cls,
        scenario_id: str,
        scenario_version: str,
        scenario_digest: str,
        ground_truth: Mapping[str, Any],
        artifacts: Iterable[EvidenceArtifact],
        limitations: Iterable[str] = (),
    ) -> EvidenceBundle:
        return cls(
            scenario_id,
            scenario_version,
            scenario_digest,
            _canonical_json(ground_truth),
            tuple(artifacts),
            tuple(limitations),
        )

    def artifacts_of_kind(self, kind: str) -> tuple[EvidenceArtifact, ...]:
        return tuple(artifact for artifact in self.artifacts if artifact.kind == kind)

    def admissible_artifacts(self, kind: str) -> tuple[EvidenceArtifact, ...]:
        return tuple(
            artifact
            for artifact in self.artifacts_of_kind(kind)
            if artifact.level is not EvidenceLevel.E4
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": "0.1",
                "scenario_id": self.scenario_id,
                "scenario_version": self.scenario_version,
                "scenario_digest": self.scenario_digest,
                "ground_truth": self.ground_truth,
                "artifacts": [artifact.to_mapping() for artifact in self.artifacts],
                "limitations": list(self.limitations),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, value: str) -> EvidenceBundle:
        parsed: Any = json.loads(value)
        expected_fields = {
            "schema_version",
            "scenario_id",
            "scenario_version",
            "scenario_digest",
            "ground_truth",
            "artifacts",
            "limitations",
        }
        if not isinstance(parsed, dict) or set(parsed) != expected_fields:
            raise ValueError("stored evidence fields are incompatible")
        raw: dict[str, Any] = parsed
        if raw["schema_version"] != "0.1":
            raise ValueError("stored evidence schema version is unsupported")
        if (
            not isinstance(raw["ground_truth"], dict)
            or not isinstance(raw["artifacts"], list)
            or not isinstance(raw["limitations"], list)
        ):
            raise ValueError("stored evidence field types are incompatible")
        return cls.create(
            scenario_id=raw["scenario_id"],
            scenario_version=raw["scenario_version"],
            scenario_digest=raw["scenario_digest"],
            ground_truth=raw["ground_truth"],
            artifacts=(EvidenceArtifact.from_mapping(item) for item in raw["artifacts"]),
            limitations=raw["limitations"],
        )
