from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from agentic_conformance.evidence import EvidenceBundle
from agentic_conformance.scenario import Scenario


@dataclass(frozen=True, slots=True)
class PreparedRun:
    token: str


class Adapter(ABC):
    """Non-intervening host translation and observation boundary."""

    name: str
    version: str

    @abstractmethod
    def probe(self) -> frozenset[str]:
        """Return capabilities without mutating the stack under test."""

    @abstractmethod
    def prepare(self, scenario: Scenario) -> PreparedRun:
        """Create an isolated fixture and optional passive observation."""

    @abstractmethod
    def execute(self, prepared: PreparedRun) -> None:
        """Execute the declared stack against the prepared scenario."""

    @abstractmethod
    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        """Return raw normalized evidence without a score."""

    @abstractmethod
    def cleanup(self, prepared: PreparedRun) -> None:
        """Tear down ephemeral state without changing recorded evidence."""
