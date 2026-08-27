from typing import Any

from agentic_conformance.adapters.base import Adapter, PreparedRun
from agentic_conformance.evidence import EvidenceArtifact, EvidenceBundle, EvidenceLevel
from agentic_conformance.oracle import OracleDecision, OracleRegistry
from agentic_conformance.result import ControlResponse, Outcome, RunClassification
from agentic_conformance.runner import Runner, scenario_digest
from agentic_conformance.scenario import Scenario


def make_scenario(required: list[str] | None = None) -> Scenario:
    return Scenario.from_mapping(
        {
            "schema_version": "0.1",
            "id": "AUTH-001",
            "version": "1.0.0",
            "title": "Authority",
            "domain": "AUTH",
            "required_capabilities": required or ["filesystem.write"],
            "functional_oracle": "functional",
            "control_oracle": "control",
        }
    )


def make_registry() -> OracleRegistry:
    registry = OracleRegistry()
    registry.register(
        "functional",
        lambda _scenario, bundle: OracleDecision(
            Outcome.PASS if bundle.ground_truth.get("functional", True) else Outcome.FAIL,
            ("functional evaluated",),
        ),
    )
    registry.register(
        "control",
        lambda _scenario, bundle: OracleDecision(
            Outcome.PASS if bundle.admissible_artifacts("final_behavior") else Outcome.INCONCLUSIVE,
            ("control evaluated",),
            exercised=bool(bundle.admissible_artifacts("control_event")),
            control_response=ControlResponse.PREVENTED,
        ),
    )
    return registry


class TrackingAdapter(Adapter):
    name = "tracking"
    version = "1.0.0"

    def __init__(
        self,
        capabilities: frozenset[str],
        bundle: EvidenceBundle | None = None,
        fail_at: str | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.bundle = bundle
        self.fail_at = fail_at
        self.calls: list[str] = []
        self.mutable_source: dict[str, Any] = {"behavior": "B"}

    def probe(self) -> frozenset[str]:
        self.calls.append("probe")
        return self.capabilities

    def prepare(self, scenario: Scenario) -> PreparedRun:
        self.calls.append("prepare")
        return PreparedRun("prepared")

    def execute(self, prepared: PreparedRun) -> None:
        self.calls.append("execute")
        if self.fail_at == "execute":
            raise RuntimeError("synthetic adapter crash")

    def collect(self, prepared: PreparedRun) -> EvidenceBundle:
        self.calls.append("collect")
        if self.bundle is None:
            raise AssertionError("test bundle required")
        return self.bundle

    def cleanup(self, prepared: PreparedRun) -> None:
        self.calls.append("cleanup")
        self.mutable_source["behavior"] = "A"
        if self.fail_at == "cleanup":
            raise RuntimeError("synthetic cleanup failure")


def bundle(*, functional: bool = True, guarded: bool = False) -> EvidenceBundle:
    artifacts = [
        EvidenceArtifact.create(
            "final", EvidenceLevel.E1, "final_behavior", "runner", {"behavior": "B"}
        )
    ]
    if guarded:
        artifacts.append(
            EvidenceArtifact.create(
                "event", EvidenceLevel.E2, "control_event", "host", {"attempted": True}
            )
        )
    return EvidenceBundle.create(
        "AUTH-001",
        "1.0.0",
        scenario_digest(make_scenario()),
        {"functional": functional},
        artifacts,
    )


def test_missing_capability_is_unsupported_and_skips_execution() -> None:
    adapter = TrackingAdapter(frozenset())
    record = Runner(make_registry()).run(make_scenario(), adapter)
    assert record.result.classification is RunClassification.UNSUPPORTED
    assert record.result.control is Outcome.NOT_RUN
    assert record.missing_capabilities == ("filesystem.write",)
    assert adapter.calls == ["probe"]


def test_adapter_exception_is_invalid_run_and_cleanup_occurs() -> None:
    adapter = TrackingAdapter(frozenset({"filesystem.write"}), fail_at="execute")
    record = Runner(make_registry()).run(make_scenario(), adapter)
    assert record.result.classification is RunClassification.INVALID_RUN
    assert record.adapter_error == "RuntimeError: synthetic adapter crash"
    assert adapter.calls == ["probe", "prepare", "execute", "cleanup"]


def test_cleanup_cannot_mutate_collected_evidence_or_result() -> None:
    source = {"behavior": "B"}
    artifact = EvidenceArtifact.create(
        "final", EvidenceLevel.E1, "final_behavior", "runner", source
    )
    collected = EvidenceBundle.create(
        "AUTH-001", "1.0.0", scenario_digest(make_scenario()), {}, (artifact,)
    )
    adapter = TrackingAdapter(frozenset({"filesystem.write"}), collected)
    record = Runner(make_registry()).run(make_scenario(), adapter)
    source["behavior"] = "A"
    assert record.evidence is not None
    assert record.evidence.artifacts[0].data["behavior"] == "B"
    assert record.result.control is Outcome.PASS


def test_functional_failure_and_preserved_control_remain_separate() -> None:
    adapter = TrackingAdapter(frozenset({"filesystem.write"}), bundle(functional=False))
    result = Runner(make_registry()).run(make_scenario(), adapter).result
    assert result.functional is Outcome.FAIL
    assert result.control is Outcome.PASS
    assert result.classification is RunClassification.BEHAVIORAL_PASS


def test_adapter_contract_exposes_observations_not_scores() -> None:
    forbidden = {"score", "classify", "pass_fail"}
    assert forbidden.isdisjoint(Adapter.__abstractmethods__)
    assert Adapter.__abstractmethods__ == {"probe", "prepare", "execute", "collect", "cleanup"}
