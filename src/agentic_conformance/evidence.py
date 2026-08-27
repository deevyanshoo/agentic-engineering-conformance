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


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    artifact_id: str
    level: EvidenceLevel
    kind: str
    producer: str
    data_json: str
    digest: str
    subject_digest: str | None = None

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
        return cls(
            artifact_id, level, kind, producer, data_json, _digest(data_json), subject_digest
        )

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
        data_json = _canonical_json(value["data"])
        if value["digest"] != _digest(data_json):
            raise ValueError("stored evidence digest does not match its payload")
        return cls(
            artifact_id=value["id"],
            level=EvidenceLevel(value["level"]),
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
        raw: dict[str, Any] = json.loads(value)
        return cls.create(
            scenario_id=raw["scenario_id"],
            scenario_version=raw["scenario_version"],
            scenario_digest=raw["scenario_digest"],
            ground_truth=raw["ground_truth"],
            artifacts=(EvidenceArtifact.from_mapping(item) for item in raw["artifacts"]),
            limitations=raw["limitations"],
        )
