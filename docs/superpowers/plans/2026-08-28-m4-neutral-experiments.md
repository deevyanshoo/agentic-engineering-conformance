# M4 Neutral Autonomous Experiments Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Execute a digest-bound six-trial AUTH-001 batch through current-user Windows Task Scheduler, persist independently rescorable evidence, and publish a reviewed non-ranking aggregate on a stacked private branch.

**Architecture:** A typed plan and deterministic worker extend the existing adapter/Runner/persistence boundary. A least-privilege Task Scheduler controller launches the committed worker outside the outer implementation process tree; process ancestry, source state, plan bindings, per-run outcomes, rescoring, and a terminal batch digest are recorded. The worker never modifies source and the controller never launches a host directly.

**Tech Stack:** Python 3.11+, standard library, jsonschema, pytest, Ruff, strict mypy, Git, Windows Task Scheduler, existing Codex and Claude adapters.

---

### Task 1: Persist authority and execution state

**Files:**
- Create: `docs/execution/m4-neutral-experiments.md`
- Create: `docs/superpowers/specs/2026-08-28-m4-neutral-experiments-design.md`
- Create: `docs/superpowers/plans/2026-08-28-m4-neutral-experiments.md`
- Modify: `AGENTS.md`

1. Record exact branch/PR/host/scheduler reconciliation and unchanged M1-M3 history.
2. Persist the approved scheduler architecture, threat/contamination boundary, alternatives, and non-claims.
3. Persist and maintain M4-D1 through M4-D23 with evidence, findings, and blockers.
4. Inspect `git diff --check`, commit the documentation checkpoint, and keep the branch stacked on M3.

### Task 2: Add immutable plan contract

**Files:**
- Create: `schemas/experiment-plan.schema.json`
- Create: `src/agentic_conformance/experiment_plan.py`
- Create: `tests/contract/test_experiment_plan_schema.py`
- Create: `tests/unit/test_experiment_plan.py`

1. Write failing tests for canonical digest generation, fixed alternating six-slot order, unique safe run IDs, absolute contained output paths, exact revision/scenario/fixture/adapter/CLI/model/policy bindings, retry limit zero, and mutation rejection.
2. Implement frozen typed values plus strict load/write validation and schema validation.
3. Write plans atomically and verify their canonical self-digest before use.
4. Run focused tests, Ruff, and strict mypy; commit the contract checkpoint.

### Task 3: Add sanitized environment and ancestry observation

**Files:**
- Create: `src/agentic_conformance/process_ancestry.py`
- Create: `src/agentic_conformance/observed_process.py`
- Create: `tests/unit/test_process_ancestry.py`
- Create: `tests/unit/test_observed_process.py`

1. Write failing tests for allowlisted environment fields, token/key/cookie exclusion, Windows ancestry parsing, scheduler-marker requirement, known-agent rejection, cycles/missing parents, and deterministic serialization.
2. Write failing tests for passive subprocess execution, child PID/ancestry capture, timeout/non-zero behavior, shell disabled, and unchanged `ProcessResult` semantics.
3. Implement a narrow PowerShell/CIM reader and passive `ProcessRunner` compatible class; retain only PID, parent PID, process name, executable identity, and timestamps.
4. Run focused tests and static checks; commit.

### Task 4: Add neutral worker and deterministic aggregation

**Files:**
- Create: `src/agentic_conformance/experiment_worker.py`
- Create: `src/agentic_conformance/experiment_aggregate.py`
- Modify: `src/agentic_conformance/codex_trial.py`
- Modify: `src/agentic_conformance/claude_trial.py`
- Modify: `src/agentic_conformance/trial_persistence.py`
- Create: `tests/unit/test_experiment_worker.py`
- Create: `tests/unit/test_experiment_aggregate.py`
- Modify/Create: focused trial persistence tests

1. Write failing tests for plan/source/scenario/fixture/CLI binding, clean-source checks before/between/after trials, neutral ancestry gate before host calls, worker-context auth preflight, six-slot order, unavailable-host continuation, zero retry, and atomic per-slot outcomes.
2. Add provided-run-ID support to the existing host-neutral trial persistence path without changing adapter scoring or AUTH semantics.
3. Implement worker orchestration through existing adapters and Runner; pass the passive observed process runner into both adapters.
4. Persist safe worker envelope, ancestry, run bundles/outcomes, rescore equality, deterministic aggregate, and final digest marker.
5. Add aggregate golden cases for all six classifications, functional/control counts, partial/unavailable runs, limitation/identity de-duplication, and non-ranking output.
6. Run focused and full deterministic checks; commit.

### Task 5: Add Task Scheduler controller

**Files:**
- Create: `src/agentic_conformance/experiment_scheduler.py`
- Create: `tests/unit/test_experiment_scheduler.py`

1. Write failing tests for safely quoted XML, `InteractiveToken`, `LeastPrivilege`, current-user identity, no password/highest privilege, literal executable/arguments/working directory, task naming, command digest, bounded polling, timeout, and deletion on terminal outcomes.
2. Implement an injectable scheduler command boundary around `schtasks.exe`; never provide a direct/background fallback.
3. Ensure monitoring only queries scheduler/file state and never mutates source or injects into trials.
4. Run focused and full deterministic checks; commit.

### Task 6: Pre-live review and immutable pre-live commit

**Files:**
- Modify: `docs/architecture.md`
- Modify: `AGENTS.md`
- Modify: `docs/execution/m4-neutral-experiments.md`
- Create: `reports/m4-pre-live-review.md`

1. Run Ruff format/check, strict mypy, full pytest, schema tests, worktree diff check, and branch-range diff check.
2. Ask an independent read-only reviewer to inspect scheduler neutrality, secret handling, plan binding, ancestry, process safety, adapter non-intervention, fixture isolation, scoring/rescore, atomic persistence, and non-claims.
3. Classify and remediate every blocking `VALID_CURRENT_SCOPE` finding; rerun affected/full gates.
4. Commit the reviewed pre-live implementation, update plan bindings to that exact clean revision under ignored output, and make no further source edits during measurement.

### Task 7: Execute exactly one neutral scheduled batch

**Files (ignored runtime output):**
- Create: `reports/runs/m4-neutral-*/experiment-plan.json`
- Create: scheduler record, worker envelope, six per-slot outcomes/bundles, aggregate, marker, and safe logs

1. Repeat outer non-model Codex/Claude authentication preflight and bind exact CLI/adapter/scenario/fixture/revision identities into the plan.
2. Register one least-privilege current-user Task Scheduler task, start it once, and record task name/identity/command digest/creation time.
3. Poll at a bounded interval without source mutation or host interaction until marker, terminal task failure, or batch timeout.
4. Verify exactly three Codex and three Claude slots, alternating order, no retries, atomic evidence, identical offline rescores, unchanged source revision/clean tree, and deterministic aggregate.
5. Delete the scheduled task and record deletion; if registration needs elevation/credential copying, stop `BLOCKED`.

### Task 8: Post-run review, final verification, and stacked publication

**Files:**
- Create: `reports/m4-neutral-batch.md`
- Create: `reports/m4-post-run-review.md`
- Create: `reports/m4-completion.md`
- Modify: `docs/execution/m4-neutral-experiments.md`

1. Commit only sanitized summaries/digests and limitations; keep raw run bundles ignored and historical M2/M3 results untouched.
2. Obtain a fresh independent read-only review of neutrality, immutable binding, ancestry, auth, trial count/order/retry policy, E0/E1 score, E2/E4 separation, rescore, aggregate, privacy, source immutability, and non-claims.
3. Remediate all blocking current-scope findings without rerunning valid trials; the initial plan authorizes zero replacement retries.
4. Run final Ruff format/check, strict mypy, full pytest/schema, complete branch-range `git diff --check`, status, and Git/GitHub reconciliation.
5. Commit completion, push `m4/neutral-experiments`, create a draft PR targeting `m3/claude-adapter`, verify PRIVATE/unmerged state, and record `M4_NEUTRAL_AUTONOMOUS_COMPLETE` only if every contract item holds.
