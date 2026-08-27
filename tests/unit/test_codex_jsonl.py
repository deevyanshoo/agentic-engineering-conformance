from __future__ import annotations

import json

import pytest

from agentic_conformance.adapters.codex import parse_codex_jsonl


def _line(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))


def test_jsonl_normalizes_stable_metadata_and_preserves_raw_events() -> None:
    values = [
        {"type": "thread.started", "thread_id": "thread-1"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"id": "item-1", "type": "command_execution", "command": "git status"},
        },
        {
            "type": "item.completed",
            "item": {"id": "item-2", "type": "reasoning", "text": "private material"},
        },
        {
            "type": "item.completed",
            "item": {"id": "item-3", "type": "agent_message", "text": "Done"},
        },
        {"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 3}},
        {"type": "future.event", "new_field": {"value": 1}},
    ]
    parsed = parse_codex_jsonl("\n".join(_line(value) for value in values) + "\n\n")

    assert parsed.thread_id == "thread-1"
    assert parsed.final_message == "Done"
    assert parsed.usage == {"input_tokens": 7, "output_tokens": 3}
    assert [event.category for event in parsed.events] == [
        "thread",
        "turn",
        "item",
        "item",
        "item",
        "turn",
        "unknown",
    ]
    assert parsed.events[2].item_type == "command_execution"
    assert parsed.events[3].metadata == {"item_id": "item-2", "item_type": "reasoning"}
    assert "private material" not in json.dumps(parsed.events[3].metadata)
    assert parsed.raw_events == tuple(values)


@pytest.mark.parametrize("value", ['{"type":"turn.started"}\nnot-json\n', "[]\n"])
def test_jsonl_rejects_malformed_or_non_object_lines(value: str) -> None:
    with pytest.raises(ValueError, match="line"):
        parse_codex_jsonl(value)
