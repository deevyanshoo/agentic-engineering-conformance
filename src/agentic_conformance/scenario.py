from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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

    @property
    def definition(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.definition_json)
        return value

    def to_json(self) -> str:
        return self.definition_json

    @classmethod
    def from_json(cls, value: str) -> Scenario:
        raw: dict[str, Any] = json.loads(value)
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Scenario:
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
        )
