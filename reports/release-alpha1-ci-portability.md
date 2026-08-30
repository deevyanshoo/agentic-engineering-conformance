# Release alpha.1 CI portability correction

Status: independent-review remediation verified locally; re-review and hosted CI pending

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
| R6 Local deterministic verification | complete | Ruff, strict mypy, 258 tests, Windows/Linux portability, demo/rescore, diff check |
| R7 Independent read-only review | in progress | Initial NOT READY; two blockers remediated; focused re-review pending |
| R8 Public hotfix PR and hosted CI | pending | CI must execute repository steps and pass |
| R9 Normal merge and post-merge gates | pending | Clean clone plus push-triggered main CI |
| R10 Tag, prerelease, publication record | pending | Tag remains pinned to verified release SHA |

## Root cause and correction

A persisted experiment path describes the producer host's path identity; a native `Path` describes the current reader or executor. The original implementation used the latter to answer the former question. The correction keeps the original serialized string authoritative for digest/replay, parses a separate lexical Windows/POSIX identity for validation, and requires that identity to match the native runtime before any scheduler, worker, filesystem, Git, or host-process operation.

## Independent review and disposition

Initial reviewer verdict at `04c9170f9c46e0712422fd85deecaf7cca489ae9`: `NOT READY`.

- `VALID_CURRENT_SCOPE` high: `//host/share/tool` was parsed as Windows UNC but could pass POSIX native absoluteness and reach adapter probe. Resolved by comparing parsed flavour with the runtime before local I/O or executable use; an OS-sensitive regression covers the dual-flavour spelling.
- `VALID_CURRENT_SCOPE` medium: `PurePath` normalized valid raw spellings such as `C:/aec`, `/srv//aec`, and `/srv/./aec`, causing digest mismatch. Resolved by preserving raw text separately from the comparison identity; round-trip tests cover both flavours and noncanonical absolute spellings.
- `QUESTION` low: the replay fixture is representative rather than an authentic tracked historical plan. The limitation remains explicit, and the canonical representative Windows mapping now has a pinned digest constant.

No schema, scenario, oracle, result, adapter-control, or historical evidence change was required.

## Path-semantics audit

1. Persisted cross-platform identities: `HostBinding.executable`, `ExperimentPlan.source_root`, and `ExperimentPlan.output_root`. These now use Windows/POSIX lexical recognition and comparison without rewriting serialized strings.
2. Current-runtime local paths: scheduler Python/working/plan paths, worker temporary workspace and Git paths, fixture containment/cleanup, reference-demo output, and atomic writer targets. Native `Path.resolve`, `is_relative_to`, and filesystem operations remain correct there.
3. Test-only path operations are local fixture mechanics and remain native.

`bind_plan_to_local_runtime` is required by plan writing, scheduler launch, and worker execution. It rejects foreign source/output or executable identities before source I/O, host probing, or model execution. Aggregate/inspection code may still load foreign plans.

No historical raw experiment plan is tracked in the public tree. The new fixed representative v0.1 plan fixture covers both producer flavours, preserves its precomputed mapping/digest through load/re-serialization, and documents that limitation without altering M2-M6 artifacts.

## Local verification

- Focused portability RED: three expected failures from foreign plan replay/runtime binding; separate traversal RED: two expected containment failures.
- Focused portability GREEN after review remediation: 15 passed on Windows and 15 passed in an ephemeral Linux Python 3.12 container.
- Affected plan/aggregate/scheduler/worker/M5 regressions: 64 passed.
- Ruff format: 124 files formatted.
- Ruff lint: passed.
- Strict mypy: 27 source files passed.
- Full pytest/schema/contract suite after review remediation: 258 passed in 42.64 seconds.
- Deterministic reference: `AUTH-001@1.0.0`, `GUARDED_PASS`, functional/control `PASS`/`PASS`, `offline_rescore_equal: true`; temporary synthetic evidence removed.
- `git diff --check`: passed.
- Scenarios, oracles, adapters, result classifications, schemas, plan serialization keys, and digest input mapping are unchanged.