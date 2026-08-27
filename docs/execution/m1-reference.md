# M1 Reference Conformance Vertical Slice — execution record

Updated: 2026-08-27

## Objective and authority

Build and locally verify the M1 reference vertical slice described by the bootstrap contract. Authority is, in order: current Git state, repository documents and executable contracts, deterministic tests/configuration, then the bootstrap request for requirements not yet persisted. Session memory is non-authoritative.

Initial state: the workspace was empty, was not a Git repository, and had no unexpected or private content. Git was initialized on `main`. No remote exists.

## Scope and non-goals

Scope: schemas, typed core, evidence and result semantics, functional/control oracles, host-neutral runner, abstract adapter, deterministic reference adapter, exactly six seed scenarios, tests, independent review, and final verification.

Non-goals include hosted services, dashboards, new agent runtimes or workflow DSLs, databases, telemetry/signature standards, composite scores, and all real coding-agent/host adapters. No publication or remote push is authorized.

## Execution DAG

| Node | Deliverable | Depends on | Status |
| --- | --- | --- | --- |
| D1 | Workspace reconciliation/bootstrap | — | COMPLETE |
| D2 | Authority, scope, decisions, terminology | D1 | COMPLETE |
| D3 | Scenario/run/result schemas and contract tests | D2 | COMPLETE |
| D4 | Core domain/evidence/result models | D3 | COMPLETE |
| D5 | Adapter abstraction and capability negotiation | D4 | COMPLETE |
| D6 | Functional/control oracle framework | D4 | COMPLETE |
| D7 | Deterministic reference adapter | D5, D6 | COMPLETE |
| D8 | Six scenarios and fixtures | D3, D6, D7 | COMPLETE |
| D9 | Golden classification tests | D7, D8 | COMPLETE |
| D10 | Stored-evidence rescoring tests | D6, D8 | COMPLETE |
| D11 | Full deterministic verification | D1–D10 | COMPLETE |
| D12 | Independent read-only review | D11 | COMPLETE |
| D13 | Finding disposition/remediation | D12 | COMPLETE |
| D14 | Final deterministic verification | D13 | PENDING |
| D15 | M1 completion record | D14 | PENDING |

## Decisions

- Use Python 3.11+, standard library runtime code, JSON scenarios, JSON Schema contracts, pytest, jsonschema, Ruff, and mypy.
- Use frozen typed value models internally; persisted evidence remains plain JSON.
- Keep scenario-specific deterministic scoring in an oracle registry, never in adapters.
- Reference-adapter modes create normalized observations for benchmark self-tests; they do not emulate or claim real host controls.
- Store sufficient E0/E1 evidence and identities for deterministic rescoring.
- Apache-2.0 covers the repository for M1; benchmark/spec-content licensing remains a pre-publication decision.

## Verification evidence

Intermediate D2–D6 checkpoint (2026-08-27):

- `python -m pytest tests/contract tests/unit -q` — 16 passed.
- `python -m ruff check .` — all checks passed after deterministic formatting.
- `python -m mypy src` — success, no issues in 8 source files.

D11 pre-review verification (2026-08-27):

- `python -m ruff check .` — all checks passed.
- `python -m mypy src` — success, no issues in 11 source files.
- `python -m pytest -q` — 46 passed in 1.06 seconds.

Final D14 evidence remains pending.

## Review evidence and findings

Independent read-only review completed against `6beb272..9012861`. The reviewer independently observed 46 passing tests and reported nine findings. All are dispositioned `VALID_CURRENT_SCOPE` in `reports/m1-review.md`; all nine have regression-tested remediations. Independent follow-up review is pending. No finding is deferred.

## Blockers and completion state

Unresolved blockers: none.

Completion state: IN_PROGRESS. This repository is not MERGE_READY or PUBLIC.
