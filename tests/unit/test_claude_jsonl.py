from __future__ import annotations

import json

import pytest

from agentic_conformance.adapters.claude import parse_claude_jsonl


def _line(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))


def test_jsonl_normalizes_text_free_lifecycle_and_preserves_raw_events() -> None:
    values = [
        {
            "type": "system",
            "subtype": "init",
            "session_id": "session-1",
            "model": "claude-sonnet-test",
            "tools": ["Read", "Edit"],
        },
        {
            "type": "assistant",
            "session_id": "session-1",
            "message": {
                "model": "claude-sonnet-test",
                "content": [
                    {"type": "thinking", "thinking": "private reasoning"},
                    {"type": "text", "text": "Working on it"},
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Edit",
                        "input": {"file_path": "src/behavior.json", "new": "private input"},
                    },
                ],
                "usage": {"input_tokens": 8, "output_tokens": 3},
            },
        },
        {
            "type": "user",
            "session_id": "session-1",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-1",
                        "is_error": False,
                        "content": "private tool output",
                    }
                ]
            },
        },
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session-1",
            "is_error": False,
            "result": "Completed",
            "num_turns": 2,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
        {"type": "future_event", "payload": {"text": "private future text"}},
    ]

    parsed = parse_claude_jsonl("\n".join(_line(value) for value in values) + "\n\n")

    assert parsed.session_id == "session-1"
    assert parsed.model == "claude-sonnet-test"
    assert parsed.final_message == "Completed"
    assert parsed.usage == {"input_tokens": 10, "output_tokens": 5}
    assert parsed.raw_events == tuple(values)
    assert [event.category for event in parsed.events] == [
        "system",
        "assistant",
        "user",
        "result",
        "unknown",
    ]
    assert parsed.events[1].tool_events == (
        {"id": "tool-1", "name": "Edit", "status": "requested"},
    )
    assert parsed.events[2].tool_events == ({"id": "tool-1", "name": None, "status": "completed"},)
    normalized = json.dumps(
        [
            {
                "type": event.event_type,
                "subtype": event.subtype,
                "category": event.category,
                "tool_events": list(event.tool_events),
                "metadata": dict(event.metadata),
            }
            for event in parsed.events
        ]
    )
    for private in (
        "private reasoning",
        "Working on it",
        "private input",
        "private tool output",
        "private future text",
    ):
        assert private not in normalized


@pytest.mark.parametrize("value", ['{"type":"system"}\nnot-json\n', "[]\n"])
def test_jsonl_rejects_malformed_or_non_object_lines(value: str) -> None:
    with pytest.raises(ValueError, match="line"):
        parse_claude_jsonl(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        _line({"type": "system", "subtype": "init"}),
        _line(
            {
                "type": "result",
                "subtype": "error_max_turns",
                "is_error": True,
                "result": "not admissible",
            }
        ),
    ],
)
def test_jsonl_rejects_incomplete_or_failed_terminal_stream(value: str) -> None:
    with pytest.raises(ValueError, match=r"empty|terminal"):
        parse_claude_jsonl(value)
