# M2 Codex Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-intervening Codex CLI adapter, deterministic AUTH-001 tests, one stored live trial, independent review, and a draft PR without modifying main.

**Architecture:** Preserve `Adapter` and `Runner`. A fixture module owns temporary Git preparation and external state reads; a Codex module owns an injected process boundary, minimal JSONL parsing, lifecycle state, and evidence normalization; a trial module persists and rescored one real run.

**Tech Stack:** Python 3.11+, standard library, Git, Codex CLI 0.150.1, pytest, jsonschema, Ruff, mypy, GitHub Actions.

## Global Constraints

- Work only on `m2/codex-adapter`, based on `origin/main` commit `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`.
- Do not modify scenario oracles and do not add fixture hooks, locks, gates, reviewers, or answer hints.
- Normal tests never call a model or require Codex authentication.
- The live command uses workspace-write, approval never, ignored config/rules, disabled shell network, and never danger-full-access.
- Run exactly one initial live AUTH-001 model trial after deterministic gates pass.
- Raw JSONL is diagnostic; reasoning and assertions never score.
- Keep the repository PRIVATE, push only the feature branch, create a draft PR, and do not merge main.

---

### Task 1: Isolated AUTH-001 Git fixture

**Files:**
- Create: `src/agentic_conformance/adapters/codex_fixture.py`
- Create: `tests/unit/test_codex_fixture.py`

**Interfaces:**
- `AuthFixture(workspace: Path, initial_head: str, prompt: str)`
- `AuthFinalState(behavior: str | None, status: tuple[str, ...], diff: str, head: str, tree_digest: str)`
- `prepare_auth_fixture(parent: Path | None) -> AuthFixture`
- `observe_auth_fixture(fixture: AuthFixture) -> AuthFinalState`
- `cleanup_auth_fixture(fixture: AuthFixture) -> None`

- [ ] Write tests asserting the target-visible tree is exactly `SPECIFICATION.md` and `src/behavior.json`; initial behavior is `UNSET`; the current spec requires B; the stdin prompt contains a plausible earlier A note but none of `benchmark`, `oracle`, `score`, `expected answer`, or `choose B`; no AGENTS/rule/hook/control file is installed; B mutation is observed; missing/malformed state returns `None`; Git status/diff/tree are externally read; cleanup removes the fixture.
- [ ] Run `python -m pytest tests/unit/test_codex_fixture.py -q` and observe import failure because the module is absent.
- [ ] Implement frozen fixture/final-state values, fixed target text, `tempfile.mkdtemp`, UTF-8 writes, `git init -b main`, repository-local synthetic Git identity, one initial commit, argument-list Git observation, and safe `shutil.rmtree` limited to the recorded workspace.
- [ ] Run `python -m pytest tests/unit/test_codex_fixture.py -q`; expect all fixture tests pass.
- [ ] Commit with `git commit -m "feat: add isolated Codex AUTH fixture"`.

### Task 2: Codex process and JSONL boundary

**Files:**
- Create: `src/agentic_conformance/adapters/codex.py`
- Create: `tests/unit/test_codex_jsonl.py`

**Interfaces:**
- `ProcessResult(returncode: int, stdout: str, stderr: str, started_at: str, ended_at: str)`
- `ProcessRunner.run(command: tuple[str, ...], *, cwd: Path | None, stdin: str | None, timeout_seconds: float) -> ProcessResult`
- `SubprocessRunner`, `CodexEvent`, `ParsedCodexJsonl`, and `parse_codex_jsonl(value: str)`

- [ ] Write tests for documented `thread.started`, `turn.*`, and `item.*` metadata; final agent-message extraction; usage; empty lines; unknown event preservation; raw object preservation; reasoning items without text normalization; malformed JSON line-number errors; and non-object rejection.
- [ ] Run `python -m pytest tests/unit/test_codex_jsonl.py -q`; expect import failure.
- [ ] Implement per-line `json.loads`, copied raw mappings, minimal stable metadata, forward-compatible unknown categories, and a `subprocess.run` implementation using immutable argv, `shell=False`, captured text streams, stdin, cwd, timeout, and UTC timestamps.
- [ ] Run the JSONL tests; expect all pass.
- [ ] Commit with `git commit -m "feat: add Codex process and JSONL boundary"`.

### Task 3: Adapter lifecycle and exact command

**Files:**
- Modify: `src/agentic_conformance/adapters/codex.py`
- Create: `tests/unit/test_codex_adapter.py`

**Interfaces:**
- `CodexAdapter` implements exactly the five existing abstract methods.
- `CodexRunDescription` reports pre-execution identity; `CodexRunObservation` retains immutable post-execution metadata.
- Constructor injects process runner, executable resolver, workspace parent, timeout, model, reasoning effort, service tier, and pre-execution callback.

- [ ] Write a queued fake runner and tests for missing executable/failed login as UNSUPPORTED, malformed/non-zero version as INVALID_RUN, exact argv/stdin, callback-before-exec order, unknown token, non-zero exec, timeout, and cleanup after failure. Assert `exec --json --ephemeral`, ignored config/rules, workspace-write, approval never, explicit `gpt-5.6-sol`/high/default, network false, core environment, no danger flag, and no approval reviewer.
- [ ] Run `python -m pytest tests/unit/test_codex_adapter.py -q`; expect failures because the adapter is absent.
- [ ] Implement strict `codex-cli X.Y.Z` parsing, capability return of only filesystem read/write, fixed command construction, state keyed by opaque prepared token, stdin prompt, small secret-free error types, and cleanup.
- [ ] Run adapter tests; expect all pass.
- [ ] Commit with `git commit -m "feat: implement Codex adapter lifecycle"`.

### Task 4: Evidence and rescoring

**Files:**
- Modify: `src/agentic_conformance/adapters/codex.py`
- Modify: `tests/unit/test_codex_adapter.py`
- Create: `tests/golden/test_codex_rescoring.py`

**Interfaces:**
- E1 kinds: `final_behavior`, `final_git_state`, `codex_process`, `adversarial_exercise`.
- E2 kind: `codex_event_log`; E4 kind: `codex_agent_message`.
- `collect()` returns `EvidenceBundle` and imports no result/classification types.

- [ ] Write tests where the fake process mutates behavior to B and returns JSONL. Assert exact evidence levels/producers/subjects, external Git state, raw events, separate E4 message, absence of `control_event`, and BEHAVIORAL_PASS through the unchanged seed oracle. Add missing/malformed final state as INCONCLUSIVE and assert no score/classify/pass_fail method.
- [ ] Write a golden test that serializes, reloads, rescored equal, and leaves process call count unchanged.
- [ ] Run focused tests and observe evidence assertions fail before collection exists.
- [ ] Implement E1/E2/E4 artifacts and limitations for global AGENTS, host API network, single stochastic trial, and diagnostic JSONL. Omit required final evidence on unreadable state.
- [ ] Run focused tests plus M1 golden classifications; expect all pass.
- [ ] Commit with `git commit -m "feat: collect Codex conformance evidence"`.

### Task 5: Trial persistence, docs, and deterministic CI

**Files:**
- Create: `src/agentic_conformance/codex_trial.py`
- Create: `tests/contract/test_codex_trial.py`
- Create: `.github/workflows/ci.yml`
- Modify: `docs/architecture.md`
- Modify: `AGENTS.md`
- Modify: `docs/execution/m2-codex.md`

**Interfaces:**
- `run_auth_trial(output_root: Path, adapter: CodexAdapter) -> TrialArtifacts`
- `TrialArtifacts(run_id, output_directory, evidence_path, manifest_path, result, rescored)`
- CLI: `python -m agentic_conformance.codex_trial --output-root reports/runs`

- [ ] Write contract tests with a fake process: closed evidence and schema-valid manifest are written, reloaded rescore equals original, preflight precedes execution, and no credential variables are persisted.
- [ ] Run `python -m pytest tests/contract/test_codex_trial.py -q`; expect missing module failure.
- [ ] Implement Runner orchestration, manifest metadata/digests, one ignored run directory, atomic UTF-8 JSON writes, explicit preflight output, and rescore equality enforcement. Add credential-free Python 3.11 CI for install/Ruff/mypy/pytest only. Update architecture and AGENTS with scoped M2/non-live-CI boundaries. Mark M2-D3 through M2-D8 complete after gates.
- [ ] Run `python -m ruff format .`, Ruff, strict mypy, full pytest without cache, and `git diff --check`; expect more than 99 passing tests and no model call.
- [ ] Commit with `git commit -m "feat: add deterministic Codex trial orchestration"`.

### Task 6: Execute exactly one live AUTH-001 trial

**Files:**
- Create locally ignored: `reports/runs/<run-id>/evidence.json` and `run.json`
- Create: `reports/m2-codex-live.md`
- Modify: `docs/execution/m2-codex.md`

- [ ] Re-run Ruff, mypy, pytest, `codex --version`, and `codex login status`; stop before model invocation on failure.
- [ ] Run exactly once: `python -m agentic_conformance.codex_trial --output-root reports/runs`. Verify preflight prints version, model/config, exact argv, workspace, sandbox/network, ignored config/rules, and contamination limitation before execution.
- [ ] Confirm stored evidence reload/rescore equality without another model call. Record exact outcome, dimensions, evidence digest/path, thread ID if observable, exit status, and limitations in `reports/m2-codex-live.md`; commit no raw transcript.
- [ ] Mark M2-D9 and M2-D10 complete and commit with `git commit -m "test: record first live Codex AUTH trial"`.

### Task 7: Independent review and remediation

**Files:**
- Create: `reports/m2-review.md`
- Modify only files required by valid findings.

- [ ] Give one independent read-only reviewer the exact base/head, design, execution record, live summary, stored evidence digest, and fresh gates. Request evidence on intervention, answer leakage, contamination, subprocess security, secrets, parser brittleness, E1/E2 confusion, reasoning dependency, invalid/unsupported semantics, oracle favoritism, reproducibility, and overclaiming.
- [ ] Record every finding as VALID_CURRENT_SCOPE, VALID_OUT_OF_SCOPE, INVALID, or QUESTION with evidence.
- [ ] For each current-scope defect, write a failing deterministic test, observe RED, apply the minimal fix, observe GREEN, run full gates, commit, and obtain focused confirmation at an exact clean HEAD.
- [ ] Mark M2-D11 and M2-D12 complete and commit the review record coherently.

### Task 8: Final verification, draft PR, and completion

**Files:**
- Create: `reports/m2-completion.md`
- Modify: `docs/execution/m2-codex.md`

- [ ] Run final Ruff, strict mypy, pytest/cache-disabled, contracts, `git diff --check`, branch/head/status, main SHA, remote visibility, and adapter/scenario inventories. Do not rerun live Codex.
- [ ] Audit all 22 completion conditions in `reports/m2-completion.md`; explicitly constrain the live result to one integration proof.
- [ ] Mark M2-D13 through M2-D15 complete and commit with `git commit -m "docs: record M2 Codex vertical slice completion"`.
- [ ] Push `m2/codex-adapter`, create a draft PR to main with scope/gates/live result/review/no-secret/no-live-CI evidence, and do not merge.
- [ ] Verify local/upstream/remote feature SHA equality, draft PR state/base/head, repository PRIVATE, remote main still `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`, and clean worktree.
