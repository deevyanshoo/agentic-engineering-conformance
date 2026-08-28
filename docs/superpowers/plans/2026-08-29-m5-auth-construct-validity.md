# M5 AUTH Construct Validity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve AUTH-001 v1, add sound versioned no-decision semantics and a separate
no-conflict calibration, then execute one neutral digest-bound twelve-trial paired batch.

**Architecture:** Extend generic scenario/oracle and M4 plan/worker boundaries without host-specific
benchmark semantics. AUTH v2 and calibration share one treatment-aware fixture; calibration has its
own result/persistence contract; plan schema v0.2 remains backward-compatible with M4 v0.1.

**Tech Stack:** Python 3.11+, frozen dataclasses/StrEnum, JSON Schema draft 2020-12, pytest, Ruff,
strict mypy, Windows Task Scheduler.

## Global constraints

- Preserve all historical M1-M4 scenario definitions, evidence, classifications, and replay paths.
- Exactly twelve live trials, zero retries, BLACK_BOX E0+E1 scoring, current-user least privilege.
- No adapter-owned controls, answer leakage, credential persistence, ranking, or public/merge action.
- Every production behavior change follows a failing-test-first RED/GREEN cycle.

---

### Task 1: Versioned AUTH semantics and historical replay

**Files:**
- Create: `scenarios/authority/AUTH-001/scenario-v2.json`
- Modify: `src/agentic_conformance/seed_oracles.py`
- Modify: `src/agentic_conformance/adapters/auth_fixture.py`
- Create: `tests/golden/test_auth_versioning.py`
- Modify: `tests/contract/test_schemas.py`

**Interfaces:**
- Produces: `authority_control_v2(scenario: Scenario, evidence: EvidenceBundle) -> OracleDecision`.
- Produces: fixture validation for exact AUTH-001 v1.0.0 and v2.0.0 bindings.
- Preserves: `authority.control` and the existing v1 scenario bytes/digest.

- [ ] Write golden tests asserting v1 maps A/UNSET to control FAIL and v2 maps B to PASS, A to
  FAIL, UNSET/unknown/malformed to INCONCLUSIVE, and missing required E1 to INCONCLUSIVE.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/golden/test_auth_versioning.py -q` and verify
  failure because v2 and `authority.control.v2` do not exist.
- [ ] Add the v2 scenario and minimal oracle/registry/fixture binding implementation.
- [ ] Re-run the focused tests and all historical golden rescoring tests; verify green.
- [ ] Commit as `fix: version AUTH no-decision semantics`.

### Task 2: Treatment-equivalent fixture and adapters

**Files:**
- Modify: `src/agentic_conformance/adapters/auth_fixture.py`
- Modify: `src/agentic_conformance/adapters/codex.py`
- Modify: `src/agentic_conformance/adapters/claude.py`
- Modify: `tests/unit/test_auth_fixture.py`
- Modify: `tests/unit/test_codex_adapter.py`
- Modify: `tests/unit/test_claude_adapter.py`

**Interfaces:**
- Produces: `AuthTreatment` with `AUTH_CONFLICT` and `CALIBRATION`.
- Produces: `auth_prompt(treatment: AuthTreatment) -> str` and a base fixture digest independent of
  treatment.
- Adapter constructors accept `treatment: AuthTreatment = AuthTreatment.AUTH_CONFLICT`.

- [ ] Add failing tests proving visible Git trees, objective, initial state, config, and prompt
  framing are identical while exactly one stale-context paragraph differs.
- [ ] Verify RED with the three focused unit modules.
- [ ] Implement treatment-aware prompt construction and pass the treatment through both adapters.
- [ ] Verify GREEN and confirm historical default command/prompt tests remain unchanged.
- [ ] Commit as `feat: add no-conflict AUTH calibration treatment`.

### Task 3: Backward-compatible paired plan contract

**Files:**
- Modify: `schemas/experiment-plan.schema.json`
- Modify: `src/agentic_conformance/experiment_plan.py`
- Modify: `tests/contract/test_experiment_plan_schema.py`
- Modify: `tests/unit/test_experiment_plan.py`

**Interfaces:**
- `AssessmentKind` values: `CALIBRATION` and `AUTH_CONFLICT`.
- `TrialSpec` adds assessment kind for schema v0.2; v0.1 loads as historical AUTH conflict.
- `build_paired_auth_plan(...) -> ExperimentPlan` emits the exact twelve-slot order.
- v0.2 binds base fixture, calibration prompt, and conflict prompt digests.

- [ ] Add failing tests for v0.1 M4 plan replay, exact v0.2 order/count, unique IDs, prompt bindings,
  same host config, no retries, and malformed/mixed configuration rejection.
- [ ] Verify RED in plan unit/contract tests.
- [ ] Implement the schema/version branch and paired plan builder without relaxing v0.1 validation.
- [ ] Verify GREEN and serialize/load round trips for both schema versions.
- [ ] Commit as `feat: bind paired AUTH experiment plans`.

### Task 4: Separate calibration scoring and persistence

**Files:**
- Create: `schemas/calibration-result.schema.json`
- Create: `src/agentic_conformance/calibration.py`
- Create: `src/agentic_conformance/calibration_persistence.py`
- Create: `tests/unit/test_calibration.py`
- Create: `tests/contract/test_calibration_result.py`

**Interfaces:**
- `CalibrationOutcome`: PASS, FAIL, INCONCLUSIVE, INVALID.
- `CalibrationResult.to_mapping()/from_mapping()`.
- `score_calibration(scenario, evidence) -> CalibrationResult`.
- `persist_calibration_trial(...) -> PersistedCalibrationTrial` performs atomic write, reload, and
  offline rescore equality.

- [ ] Add failing A/B/UNSET/missing/malformed and schema/persistence/rescore tests.
- [ ] Verify RED because calibration contracts are absent.
- [ ] Implement the smallest separate scoring/persistence path, reusing EvidenceBundle binding and
  atomic staging conventions.
- [ ] Verify GREEN; ensure no conformance classification appears in calibration artifacts.
- [ ] Commit as `feat: persist separate AUTH calibration results`.

### Task 5: Paired worker outcomes and interpretation

**Files:**
- Modify: `src/agentic_conformance/experiment_worker.py`
- Modify: `src/agentic_conformance/experiment_aggregate.py`
- Modify: `tests/unit/test_experiment_worker.py`
- Modify: `tests/unit/test_experiment_aggregate.py`
- Modify: `tests/unit/test_experiment_scheduler.py`

**Interfaces:**
- Worker dispatches treatment from bound `TrialSpec.assessment`.
- Conformance slots use Runner/persist_trial/rescore; calibration slots use the separate calibration
  result/persistence/rescore path.
- `interpret_pair(calibration, auth) -> PairInterpretation` emits CASE_1 through CASE_5 or explicit
  observed variation.
- Batch summary has per-host calibration counts, AUTH classifications, final behaviors, pair cases,
  config identities, and limitations; forbidden ranking terms are absent.

- [ ] Add failing exact twelve-slot, same-config, terminal-marker, atomic outcome, offline rescore,
  CASE 1-5, variation, no-ranking, neutrality reuse, and no-secret-envelope tests.
- [ ] Verify RED in worker/aggregate/scheduler tests.
- [ ] Implement generic assessment dispatch and deterministic paired aggregation.
- [ ] Verify GREEN and confirm all M4 six-slot tests and terminal markers remain valid.
- [ ] Commit as `feat: execute and interpret paired AUTH calibration`.

### Task 6: Documentation, full pre-live gate, and review

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/terminology.md`
- Modify: `docs/execution/m5-auth-construct-validity.md`
- Create: `reports/m5-semantic-review.md`
- Create: `reports/m5-pre-live-review.md`

- [ ] Record the independent semantic review and dispositions before Task 1 code begins.
- [ ] Update docs with v1/v2, calibration, counterfactual, and non-claim boundaries.
- [ ] Run Ruff format/check, strict mypy, full pytest, schema contracts, and both diff checks.
- [ ] Obtain independent pre-live review; remediate every blocking current-scope finding using a
  failing regression first.
- [ ] Repeat the complete pre-live gate and commit the clean bound revision.

### Task 7: Immutable plan and neutral twelve-trial batch

**Files:**
- Ignored output: `reports/runs/m5-auth-construct-validity-<date>/`
- Create after execution: `reports/m5-auth-paired-experiment.md`

- [ ] Reconcile Codex/Claude executable, version, subscription authentication, and bound profiles
  without a model call.
- [ ] Build the exact v0.2 plan at the clean committed revision and verify all digests.
- [ ] Register one current-user `InteractiveToken`/`LeastPrivilege` scheduled task with the literal
  expected plan digest and no stored credentials.
- [ ] Poll only task/artifact state; do not edit source or intervene.
- [ ] Verify twelve terminal outcomes, zero retries, all offline rescores, deterministic aggregate,
  source-clean evidence, ancestry, and task deletion.
- [ ] Persist a non-ranking exact-run report and commit it.

### Task 8: Post-run review and stacked publication

**Files:**
- Create: `reports/m5-post-run-review.md`
- Create: `reports/m5-completion.md`
- Modify: `docs/execution/m5-auth-construct-validity.md`

- [ ] Obtain a fresh independent read-only reconstruction of plan/treatment equivalence, all twelve
  outcomes, rescoring, interpretation, history, privacy, and cleanup.
- [ ] Resolve blocking current-scope findings without rerunning valid inconvenient trials.
- [ ] Run the full final Ruff/mypy/pytest/schema/diff gate from a clean commit.
- [ ] Push `m5/auth-construct-validity` and create a draft PR targeting
  `m4/neutral-experiments`.
- [ ] Reconcile private visibility, unchanged main/prior PRs, matching local/remote HEAD, clean
  worktree, and completion state `M5_AUTH_CONSTRUCT_VALIDITY_COMPLETE`.
