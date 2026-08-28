from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).parents[2]


def _schema() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(
        (ROOT / "schemas/experiment-plan.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(value)
    return value


def _valid() -> dict[str, Any]:
    hosts = []
    for host in ("codex", "claude"):
        hosts.append(
            {
                "name": host,
                "adapter_version": "1.0.0",
                "cli_version": "2.0.0",
                "executable": f"C:/tools/{host}.CMD",
                "requested_model": f"{host}-model",
                "config_digest": "sha256:" + "d" * 64,
                "sandbox_policy": f"{host}-restricted-workspace",
            }
        )
    order = (("codex", 1), ("claude", 1), ("codex", 2), ("claude", 2), ("codex", 3), ("claude", 3))
    return {
        "schema_version": "0.1",
        "batch_id": "m4-neutral-20260828",
        "label": "NEUTRAL_AUTONOMOUS_BASELINE",
        "benchmark_revision": "a" * 40,
        "source_root": "C:/workspace",
        "output_root": "C:/workspace/reports/runs/m4-neutral-20260828",
        "scenario": {"id": "AUTH-001", "version": "1.0.0", "digest": "sha256:" + "b" * 64},
        "fixture": {"version": "1.0.0", "digest": "sha256:" + "c" * 64},
        "observation_mode": "BLACK_BOX",
        "network_policy": "RESTRICTED",
        "retry_limit": 0,
        "randomization": "alternating-codex-first-v1",
        "created_at": "2026-08-28T12:00:00Z",
        "hosts": hosts,
        "trials": [
            {
                "sequence": sequence,
                "run_id": f"m4-neutral-20260828-{host}-{ordinal}",
                "host": host,
                "ordinal": ordinal,
            }
            for sequence, (host, ordinal) in enumerate(order, start=1)
        ],
        "plan_digest": "sha256:" + "e" * 64,
    }


def test_experiment_plan_schema_accepts_complete_contract() -> None:
    Draft202012Validator(_schema()).validate(_valid())


@pytest.mark.parametrize(
    "mutation",
    [
        {"retry_limit": 1},
        {"observation_mode": "PASSIVE_INSTRUMENTED"},
        {"label": "HOST_RANKING"},
    ],
)
def test_experiment_plan_schema_rejects_forbidden_contracts(
    mutation: dict[str, object],
) -> None:
    value = {**_valid(), **mutation}
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(value)
