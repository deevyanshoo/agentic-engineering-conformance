# M1 Reference Conformance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, review, and locally verify the complete M1 reference conformance vertical slice.

**Architecture:** Declarative JSON scenarios feed a typed Python core. A host-neutral runner obtains normalized immutable evidence through a non-scoring adapter, while scenario-owned deterministic oracles produce separate functional and control outcomes and run classifications. Persisted evidence can be loaded and rescored without executing the adapter.

**Tech Stack:** Python 3.11+, standard library runtime, pytest, jsonschema, Ruff, mypy, JSON Schema Draft 2020-12.

## Global Constraints

- Implement exactly AUTH-001, MUT-001, COMP-002, REV-002, INV-003, and REC-001.
- Do not implement a real coding-agent adapter, network service, database, workflow DSL, composite score, or publication integration.
- Adapters never add controls and never decide PASS/FAIL.
- E4 evidence never satisfies a deterministic oracle by itself.
- Functional and control outcomes remain separate.
- No remote publication or push.

---

### Task 1: Bootstrap authority and contracts

**Files:** Create repository metadata, `docs/*.md`, `docs/decisions/*.md`, `schemas/*.json`, and `tests/contract/test_schemas.py`.

**Interfaces:** Produces JSON Schema contracts and durable project authority consumed by later tasks.

- [ ] Write contract tests that validate one minimal valid instance and reject malformed scenario, run, and result documents.
- [ ] Run `python -m pytest tests/contract/test_schemas.py -q` and confirm failure because schemas are absent.
- [ ] Add the three Draft 2020-12 schemas with closed top-level objects and honest nullable/not-observable fields.
- [ ] Run the contract test and confirm it passes.
- [ ] Inspect status/diff, update the execution record, and commit a coherent bootstrap checkpoint.

### Task 2: Typed models and evidence persistence

**Files:** Create `src/agentic_conformance/scenario.py`, `evidence.py`, `result.py`, package init, and `tests/unit/test_models.py`.

**Interfaces:** Produces `Scenario`, `EvidenceArtifact`, `EvidenceBundle`, `OracleResult`, enums, and JSON round-trip functions.

- [ ] Write unit tests for enum values, evidence provenance, immutable bundle round trips, and rejection of E4-only deterministic evidence.
- [ ] Run focused tests and confirm missing imports fail.
- [ ] Implement minimal frozen dataclasses and serialization needed by the tests.
- [ ] Run focused and contract tests; refactor only while green.
- [ ] Inspect diff and commit the model checkpoint.

### Task 3: Adapter contract, runner, and classification

**Files:** Create `adapters/base.py`, `runner.py`, `oracle.py`, and `tests/unit/test_runner.py`.

**Interfaces:** Produces `Adapter.probe/prepare/execute/collect/cleanup`, capability negotiation, `OracleRegistry.score`, `Runner.run`, and `rescore`.

- [ ] Write tests proving insufficient capability skips execution and yields UNSUPPORTED, adapter exceptions yield INVALID_RUN, cleanup cannot mutate recorded evidence, and adapters do not return scores.
- [ ] Run focused tests and verify expected missing-feature failures.
- [ ] Implement the minimal abstract adapter, orchestration, exception boundary, classification rules, and oracle registry.
- [ ] Run focused tests and then all existing tests.
- [ ] Inspect diff and commit the runner checkpoint.

### Task 4: Six scenario definitions and deterministic oracles

**Files:** Create six `scenarios/*/*/scenario.json` files, six fixture JSON files, oracle implementations, and `tests/scenarios/test_seed_scenarios.py`.

**Interfaces:** Registers oracle IDs `authority.current`, `mutation.overlap`, `completion.source_binding`, `review.candidate_binding`, `invalidation.selective`, and `reconstruction.durable_state`.

- [ ] Write parameterized tests loading and schema-validating exactly six scenario documents.
- [ ] Write failing scenario tests for stale authority, lost update, stale verification, stale review, exact dependency closure including over/under invalidation, and non-fabricating reconstruction including missing/inconsistent state.
- [ ] Run focused tests and confirm missing scenarios/oracles fail.
- [ ] Add small JSON fixtures and minimal deterministic oracle functions to pass each behavior.
- [ ] Run scenario and full tests, inspect the exact scenario count, and commit.

### Task 5: Reference adapter, golden classes, and rescoring

**Files:** Create `adapters/reference.py`, `tests/golden/test_classifications.py`, and `tests/golden/test_rescoring.py`.

**Interfaces:** Produces `ReferenceAdapter(mode, capabilities)` and stored evidence accepted by `rescore`.

- [ ] Write failing golden tests for GUARDED_PASS, BEHAVIORAL_PASS, FAIL, INCONCLUSIVE, INVALID_RUN, and UNSUPPORTED plus functional PASS/control FAIL and functional FAIL/control PASS.
- [ ] Write a failing test that executes once, serializes evidence, constructs no adapter, and obtains the identical score through `rescore`.
- [ ] Run golden tests and confirm missing reference behavior fails.
- [ ] Implement only explicit deterministic modes and evidence persistence required by those tests.
- [ ] Run golden and full tests, inspect diff, and commit.

### Task 6: Quality gates, review, and completion

**Files:** Update `pyproject.toml`, execution record, `reports/m1-review.md`, and `reports/m1-completion.md`.

**Interfaces:** Produces reproducible verification, review, finding, and completion evidence.

- [ ] Run `python -m ruff check .`, `python -m mypy src`, and `python -m pytest -q`; record exact outputs and commit the verification checkpoint.
- [ ] Dispatch one independent read-only reviewer with M1 scope, documents, exact base/head diff, and verification evidence.
- [ ] Classify every finding as VALID_CURRENT_SCOPE, VALID_OUT_OF_SCOPE, INVALID, or QUESTION in the review report.
- [ ] For every VALID_CURRENT_SCOPE finding, add a failing regression test, then implement minimal remediation and rerun focused tests.
- [ ] Run all checks fresh, update records against all 27 completion conditions, inspect status/diff, and create the final local commit.
