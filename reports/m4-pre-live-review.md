# M4 independent pre-live review

Date: 2026-08-28

Reviewer: Schrodinger, independent read-only subagent

Scope: M4 neutral worker, immutable plan, process ancestry, Task Scheduler controller,
aggregate/result persistence, privacy boundary, and deterministic tests. The reviewer did not
edit files, invoke a host model, or register a scheduled task.

## Initial disposition

The first pass returned PRE-LIVE NO-GO with seven VALID_CURRENT_SCOPE blockers:

1. subscription authentication was not bound to the immutable plan;
2. the scheduled action was not externally bound to the plan digest;
3. short version/auth probes could disappear before ancestry capture;
4. stale terminal markers were insufficiently bound to plan/state/aggregate evidence;
5. timeout did not persist a sound terminal partial-batch classification;
6. failed live invocations could lose available ancestry evidence;
7. requested model profiles were reported as though observed.

One question about per-slot outcome persistence was accepted as current-scope hardening.

## Remediation

The implementation now:

- binds sanitized auth mode/provider/subscription metadata and verifies it in outer and worker
  preflight, with exact fail-closed Codex status parsing;
- passes the immutable plan digest as a literal scheduled-task argument and rejects a recomputed
  replacement plan;
- reserves ancestry capture for live invocations while short probes use the ordinary process seam;
- rejects pre-existing runtime output, validates terminal markers against plan-bound atomic
  per-slot outcomes and a deterministically reconstructed aggregate, and fails closed;
- records digest-bound timeout partial state only after task termination succeeds;
- retains a possibly active task definition and records BLOCKED_ACTIVE_TASK if termination fails;
- records a sanitized ancestry-unavailable launch observation when ancestry capture fails after
  process creation;
- separates requested model/profile from nullable observed model identity;
- persists a uniform digest-bearing outcome for every slot and reloads outcomes from disk before
  aggregate generation;
- deletes the exact task after fully validated terminal evidence, while preserving the
  termination-failure no-delete path.

## Closure

Two closure passes found four additional cleanup/fail-closed defects. Each was remediated and
covered by launch- or process-level regression tests. The final reviewer verdict was:

PRE-LIVE GO

No VALID_CURRENT_SCOPE blocker remained.

## Verification supplied to reviewer

- Ruff format check: 74 files already formatted.
- Ruff lint: passed.
- strict mypy: 24 source files passed.
- pytest: 188 passed.
- worktree and complete M3-base-to-M4 git diff --check: passed.
- No scheduler task or live host model was invoked during review/remediation.
