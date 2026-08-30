# Continuous integration and verification

## Deterministic contributor gate

The repository-owned deterministic gate is:

```shell
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy --strict src
python -m pytest -q
```

These commands require no model account, paid subscription, model credential, or network after dependencies are installed. Normal tests make no live host trials. Scenario/schema contract checks are included in the full pytest suite.

The checked-in GitHub Actions workflow runs only installation, Ruff, mypy, and pytest. It contains no model secret and never launches Codex, Claude Code, or the neutral scheduler.

## Alpha hosted-CI status

Hosted CI success is not claimed. While the repository is private, GitHub Actions jobs have failed before repository steps because of the account's external Actions spending/capacity state. Repeated retries would not test this repository, so no green badge or required hosted status is presented.

The launch strategy is:

1. rely on recorded local and fresh-clone deterministic evidence while the repository remains private;
2. keep the deterministic workflow present but not describe it as passing or require it for publication;
3. after an authorized public visibility transition, manually dispatch exactly one deterministic workflow to learn whether public-repository hosted Actions are available;
4. claim green hosted CI only if that repository-owned run executes and passes; otherwise retain the reproducible local gate and document the external limitation.

No purchase, secret, live-model workflow, weakened test, or fabricated status is part of this strategy.