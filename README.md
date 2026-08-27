# Agentic Engineering Conformance

Agentic Engineering Conformance is an early, vendor-neutral adversarial benchmark for testing whether the engineering system surrounding a coding agent preserves its claimed control guarantees.

M1 is a deterministic reference vertical slice. It tests benchmark architecture, not model coding capability, and contains no real coding-agent adapter. The six provisional domains are authority, mutation, completion, review, invalidation, and reconstruction integrity.

## Development

Requires Python 3.11 or newer.

```text
python -m pip install -e .[dev]
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Start with [the charter](docs/charter.md), [architecture](docs/architecture.md), and [M1 execution record](docs/execution/m1-reference.md).

## Status and license

M1 is local pre-publication work. The repository is Apache-2.0 licensed. Licensing for future benchmark/specification content remains a pre-publication decision; see `NOTICE`.
