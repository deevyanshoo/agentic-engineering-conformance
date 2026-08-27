from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class Domain(StrEnum):
    AUTH = "AUTH"
    MUT = "MUT"
    COMP = "COMP"
    REV = "REV"
    INV = "INV"
    REC = "REC"


class ObservationMode(StrEnum):
    BLACK_BOX = "BLACK_BOX"
    PASSIVE_INSTRUMENTED = "PASSIVE_INSTRUMENTED"


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    version: str
    title: str
    domain: Domain
    required_capabilities: frozenset[str]
    functional_oracle: str
    control_oracle: str
    observation_mode: ObservationMode
    definition_json: str
    ground_truth_json: str

    @property
    def definition(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.definition_json)
        return value

    @property
    def ground_truth(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.ground_truth_json)
        return value

    def to_json(self) -> str:
        return self.definition_json

    @classmethod
    def from_json(cls, value: str) -> Scenario:
        raw: dict[str, Any] = json.loads(value)
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, Any], ground_truth: Mapping[str, Any] | None = None
    ) -> Scenario:
        copied: dict[str, Any] = json.loads(canonical_json(value))
        return cls(
            scenario_id=copied["id"],
            version=copied["version"],
            title=copied["title"],
            domain=Domain(copied["domain"]),
            required_capabilities=frozenset(copied["required_capabilities"]),
            functional_oracle=copied["functional_oracle"],
            control_oracle=copied["control_oracle"],
            observation_mode=ObservationMode(copied.get("observation_mode", "BLACK_BOX")),
            definition_json=canonical_json(copied),
            ground_truth_json=canonical_json(ground_truth or {}),
        )


def load_scenario(path: Path, schema_path: Path) -> Scenario:
    with path.open(encoding="utf-8") as handle:
        definition: dict[str, Any] = json.load(handle)
    with schema_path.open(encoding="utf-8") as handle:
        schema: dict[str, Any] = json.load(handle)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(definition)
    fixture_contract = definition["fixture"]
    fixture_path = schema_path.parent.parent / fixture_contract["path"]
    fixture_bytes = fixture_path.read_bytes()
    fixture_digest = f"sha256:{hashlib.sha256(fixture_bytes).hexdigest()}"
    if fixture_digest != fixture_contract["digest"]:
        raise ValueError("fixture digest does not match scenario binding")
    ground_truth: dict[str, Any] = json.loads(fixture_bytes)
    return Scenario.from_mapping(definition, ground_truth)
