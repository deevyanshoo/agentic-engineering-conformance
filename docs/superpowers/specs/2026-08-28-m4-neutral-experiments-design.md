# M4 Neutral Autonomous Experiments Design

## Purpose

M4 separates benchmark implementation from measurement by committing a complete worker, binding
one immutable six-trial plan, and asking Windows Task Scheduler to launch that worker outside the
outer coding-agent process tree. The experiment is an execution/repeatability validation of the
existing AUTH-001 benchmark, not a host comparison.

## Selected architecture

The outer controller performs read-only host preflight, writes a canonical digest-bound plan under
the ignored run-output tree, registers a single on-demand Task Scheduler definition, starts it,
and observes only scheduler state and terminal files. The action directly invokes the committed
worktree's Python interpreter with:

```text
python -m agentic_conformance.experiment_worker --plan <absolute-plan-path>
```

The task runs as the current interactive user with `InteractiveToken` and `LeastPrivilege`. It
contains explicit executable, arguments, and working directory values, no shell wrapper, embedded
credentials, stored password, or highest-privilege request. The controller deletes the task after
terminal completion or timeout and records creation/deletion metadata plus a command digest.

The worker verifies its source revision, clean tree, plan digest, scenario definition, fixture
ground truth/version, adapter versions, and observed CLI versions before spending a trial. It
captures a sanitized OS/Python/Git/host envelope and best-effort process ancestry. A known coding
agent in the worker's direct ancestry, or no scheduler/service marker, terminates the batch as
`INVALID_NEUTRAL_ENVIRONMENT` before any live call.

The six plan slots alternate Codex and Claude. Each uses a new shared AUTH fixture through the
existing adapters and host-neutral Runner. A passive process runner records the launched host PID
and allowlisted ancestry while preserving the existing process result contract. Evidence-bearing
runs use the existing atomic persistence and offline-rescore boundary. Unsupported or invalid
pre-execution slots receive explicit atomic outcome records, never fabricated evidence. There are
no retries in the initial plan.

A deterministic aggregate reader derives counts from the bound plan and persisted outcomes. It
emits classification and functional/control counts, limitations, and actually observed identities,
but no composite score, winner, ranking, or cross-host inference. A terminal marker binds the plan,
summary, and ordered outcome digests.

## Alternatives considered

1. A PowerShell `Register-ScheduledTask` command assembled at runtime could express the same task,
   but introduces extra object serialization and quoting surfaces. A generated Task Scheduler XML
   definition with literal values is smaller to validate and digest.
2. `Start-Process`, `Start-Job`, a detached child, or a background shell would remain descendants
   of the outer implementation context. They do not meet the neutral baseline and are rejected.
3. A service or separate account could create stronger isolation, but would require elevation,
   credential movement, or changed authentication. That exceeds authorization; inability to use
   current-user Task Scheduler is a blocker, not permission to downgrade.

## Security, privacy, and failure semantics

Plan and scheduler fields are typed, absolute, and validated; user-provided shell fragments are not
accepted. Environment capture is an allowlist and stores no values for token/key/cookie variables.
Raw host output remains an ignored diagnostic sidecar. E2 normalization is text-free, E4 cannot
score, and no reasoning is collected.

Worker output is staged and renamed atomically. Source dirtiness, binding drift, malformed plan,
invalid ancestry, or terminal marker inconsistency fails closed. Host unavailability in the worker
context marks that host's slots `UNSUPPORTED` and permits the other host's declared slots to
continue. Adapter/harness failure yields `INVALID_RUN`. Missing trials remain explicit; no hidden
replacement or cosmetic retry occurs.

Task Scheduler improves process/control separation but does not prove environmental independence:
the same Windows user profile, machine, network, installed binaries, authentication stores, and
administrator-managed host policy remain shared limitations.
