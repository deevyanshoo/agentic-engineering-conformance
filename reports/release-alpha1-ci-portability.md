# Release alpha.1 CI portability correction

Status: hosted-CI boundary remediation verified locally; exact-head re-review and hosted CI pending

## Authority and scope

- Objective: correct the release-blocking cross-platform validation defect exposed by public GitHub Actions, then complete `v0.1.0-alpha.1` only after every local and hosted gate is green.
- Base: public `origin/main` at `799b5ef62f2f3ebe9555608b38c325761b1efbd9`.
- Branch: `release/alpha1-ci-portability`.
- Historical M1-M6 records, experiment bundles, digests, classifications, scenarios, and oracles are immutable.
- No live Codex or Claude trial is in scope.

## Reconciliation evidence

- Repository: `deevyanshoo/agentic-engineering-conformance`, PUBLIC, default branch `main`.
- PRs #1-#5 are merged with the expected heads and merge commits; every milestone head and merge commit is an ancestor of `origin/main`.
- `v0.1.0-alpha.1` tag and release are absent.
- Failed public workflow: run `33321316261`, job `99283672234`, exact head `799b5ef62f2f3ebe9555608b38c325761b1efbd9`.
- Install, Ruff format, Ruff lint, and strict mypy passed. Pytest reported 48 failed and 195 passed.
- All observed failures originate at `experiment_plan.py:214`: native `Path(host.executable).is_absolute()` rejects persisted Windows paths on the Linux runner.
- Clean Windows baseline at the same revision: 243 tests passed.

## Execution DAG

| Node | State | Evidence |
| --- | --- | --- |
| R1 Live release/GitHub reconciliation | complete | Public state, merge ancestry, absent tag/release, and Actions run verified |
| R2 Isolated hotfix branch/worktree | complete | ignored project-local worktree, clean base `799b5ef...` |
| R3 Persisted/runtime path audit | complete | Three persisted identities separated from native runtime operations |
| R4 Failing portability tests | complete | Three expected failures observed before implementation; traversal test separately observed two expected failures |
| R5 Minimal lower-layer correction | complete | Portable lexical validation plus explicit local runtime binding |
| R6 Local deterministic verification | complete | Ruff, strict mypy, 268 tests on Windows/Linux Python 3.11, demo/rescore, diff check |
| R7 Independent read-only review | in progress | Earlier exact-head READY; hosted-CI boundary correction requires focused re-review |
| R8 Public hotfix PR and hosted CI | in progress | PR #6 opened; first run exposed premature runtime binding and was remediated without retry |
| R9 Normal merge and post-merge gates | pending | Clean clone plus push-triggered main CI |
| R10 Tag, prerelease, publication record | pending | Tag remains pinned to verified release SHA |

## Root cause and correction

A persisted experiment path describes the producer host's path identity; a native `Path` describes the current reader or executor. The original implementation used the latter to answer the former question. The correction keeps the original serialized string authoritative for digest/replay, parses a separate lexical Windows/POSIX identity for validation, and requires that identity to match the native runtime before any scheduler, worker, filesystem, Git, or host-process operation.

## Independent review and disposition

Initial reviewer verdict at `04c9170f9c46e0712422fd85deecaf7cca489ae9`: `NOT READY`.

- `VALID_CURRENT_SCOPE` high: `//host/share/tool` was parsed as Windows UNC but could pass POSIX native absoluteness and reach adapter probe. Resolved by comparing parsed flavour with the runtime before local I/O or executable use; an OS-sensitive regression covers the dual-flavour spelling.
- `VALID_CURRENT_SCOPE` medium: `PurePath` normalized valid raw spellings such as `C:/aec`, `/srv//aec`, and `/srv/./aec`, causing digest mismatch. Resolved by preserving raw text separately from the comparison identity; round-trip tests cover both flavours and noncanonical absolute spellings.
- `QUESTION` low: the replay fixture is representative rather than an authentic tracked historical plan. The limitation remains explicit, and the canonical representative Windows mapping now has a pinned digest constant.

Focused re-review verdict at `bc7012e6c543d3b5ef48ee1488202568449f92ed`: `NOT READY`.

- `VALID_CURRENT_SCOPE` medium: exact concrete-class comparison rejected mixed canonical/noncanonical paths of the same flavour. Resolved by comparing Windows-versus-POSIX flavour, with both-flavour regressions.
- `VALID_CURRENT_SCOPE` medium: validation resolved a digest-bound persisted root containing a lexical parent segment, so the returned mapping no longer matched its digest. Resolved by retaining the exact persisted spelling through every validation/revalidation; local resolution occurs only in runtime binding.
- `VALID_CURRENT_SCOPE` medium: source/output resolution preceded executable-flavour rejection. Resolved by parsing and checking all source, output, and executable identities before any native `Path.resolve()` call; an ordering regression makes resolution fail if reached early.

Final exact-commit review verdict at `dad9a63ec75e5b43581bdcbf0ff6961816b3a3c7`: `READY`, with no remaining `VALID_CURRENT_SCOPE` findings. The reviewer independently reproduced stable mapping/digest behavior, exercised Windows/POSIX/UNC and malformed-path edges, confirmed existing plan equality contracts, and verified that all runtime flavours are rejected before native resolution or I/O.

The first PR workflow at head `7afbc58dc30ef9506709e33bb0cbf1b62ea3fd26` (run `33326841914`, job `99298389337`) executed all repository setup, Ruff, and mypy steps, then reported 18 failed and 245 passed tests. The remaining failure was boundary placement: plan writing and injected deterministic runtime seams were incorrectly required to use current-OS host executables. The compatibility check now applies only when `run_experiment` selects its default real-host runtime; portable plan persistence remains OS-neutral, and an explicit injected runtime remains a non-executing deterministic seam. The default worker still rejects a foreign executable before native resolution, source I/O, adapter probing, or subprocess execution.

Focused boundary re-review verdict at `ea63a2bab0b6690bd4e298c4ddcba87b6b027d63`: `NOT READY` with one high `VALID_CURRENT_SCOPE` finding. Passing `default_runtime_factory` explicitly bypassed the first boundary correction because locality was inferred from `runtime_factory is None`. The worker now requires local executable flavour by default for every factory. A narrowly named test-only opt-in requires both a non-default factory and an adapter process runner that explicitly declares `executes_subprocess = False`; the worker validates that marker before adapter probe. Regressions cover the explicit default factory and a wrapped in-tree subprocess factory, so neither can bypass locality enforcement.

Second focused boundary re-review verdict at `1bcaed66ecbb981c6533a6c77a8520b071fd6063`: `NOT READY` with one medium `VALID_CURRENT_SCOPE` finding. The returned runner marker was checked only after arbitrary factory construction code could execute. The test-only opt-in now requires the factory function itself to declare `executes_subprocess = False`, and the worker validates that marker before invoking it. The returned runner marker remains a defense-in-depth check before adapter probe. An eager unmarked-factory regression proves the factory is never called.

No schema, scenario, oracle, result, adapter-control, canonical serialization, digest input, or historical evidence change was required.

## Path-semantics audit

1. Persisted cross-platform identities: `HostBinding.executable`, `ExperimentPlan.source_root`, and `ExperimentPlan.output_root`. These now use Windows/POSIX lexical recognition and comparison without rewriting serialized strings.
2. Current-runtime local paths: scheduler Python/working/plan paths, worker temporary workspace and Git paths, fixture containment/cleanup, reference-demo output, and atomic writer targets. Native `Path.resolve`, `is_relative_to`, and filesystem operations remain correct there.
3. Test-only path operations are local fixture mechanics and remain native.

`bind_plan_to_local_runtime` is required by plan writing, scheduler launch, and worker execution. It rejects foreign source/output or executable identities before source I/O, host probing, or model execution. Aggregate/inspection code may still load foreign plans.

No historical raw experiment plan is tracked in the public tree. The new fixed representative v0.1 plan fixture covers both producer flavours, preserves its precomputed mapping/digest through load/re-serialization, and documents that limitation without altering M2-M6 artifacts.

## Local verification

- Focused portability RED: three expected failures from foreign plan replay/runtime binding; separate traversal RED: two expected containment failures.
- Focused portability GREEN after both review remediations: 20 passed on Windows and 20 passed in an ephemeral Linux Python 3.12 container.
- Affected plan/aggregate/scheduler/worker/M5 regressions: 69 passed.
- Ruff format: 124 files formatted.
- Ruff lint: passed.
- Strict mypy: 27 source files passed.
- Full pytest/schema/contract suite after pre-invocation factory validation: 268 passed on Windows in 44.23 seconds and 268 passed in a Git-equipped ephemeral Linux Python 3.11.16 container in 10.74 seconds.
- Deterministic reference: `AUTH-001@1.0.0`, `GUARDED_PASS`, functional/control `PASS`/`PASS`, `offline_rescore_equal: true`; temporary synthetic evidence removed.
- `git diff --check`: passed.
- Scenarios, oracles, adapters, result classifications, schemas, plan serialization keys, and digest input mapping are unchanged.
