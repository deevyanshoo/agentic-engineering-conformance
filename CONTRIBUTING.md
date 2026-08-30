# Contributing

Thank you for helping improve Agentic Engineering Conformance. The project values small, evidence-backed changes over scope expansion.

## Before opening a change

- Read the [charter](docs/charter.md), [architecture](docs/architecture.md), [claims](docs/claims.md), and [evidence policy](docs/evidence-policy.md).
- Keep examples synthetic and domain-neutral.
- Open an issue first for a new domain, real-host scenario, dependency, or contract change. Alpha maintainers may defer scope even when implementation is straightforward.
- Never include credentials, raw host transcripts, proprietary data, private reasoning, or unrelated repository material.

## Development setup

Python 3.11 or newer is required.

```shell
python -m venv .venv
# POSIX: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Deterministic contributor gate

Every ordinary change must pass:

```shell
python -m ruff format --check .
python -m ruff check .
python -m mypy --no-incremental src
python -m pytest -q -p no:cacheprovider
```

Schema validation and contract checks are part of pytest. Run `git diff --check` before committing. No paid model account is required for this gate.

## Live-host validation

Codex, Claude Code, and neutral Windows experiments are optional maintainer validation. Do not run them in normal tests, CI, or a contribution unless a maintainer explicitly approves a bound plan. Never add model credentials to GitHub Actions or the repository.

## Change guidance

- Production behavior changes use a failing test first.
- Preserve functional and control outcomes as separate dimensions.
- Adapters launch and observe; they never score or add controls.
- E4 assertions never satisfy deterministic oracles alone.
- Version scenario semantic changes; never make historical evidence unreplayable.
- Keep dependencies minimal and explain any addition.

See [scenario contributions](docs/contributing-scenarios.md) and [adapter contributions](docs/contributing-adapters.md).

## Pull requests

Use a focused branch, explain the invariant and evidence boundary, list exact verification commands/outcomes, disclose limitations, and confirm the privacy checklist in the template. Contributions are licensed under Apache-2.0 as described in [licensing](docs/licensing.md).