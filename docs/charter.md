# Charter and scope

Agentic Engineering Conformance evaluates whether a declared engineering stack around a coding agent preserves its claimed engineering-control invariants under adversarial, interrupted, conflicting, or changing conditions. The unit under test may include a model, host, repository instructions, workflow, tools, isolation strategy, CI/review configuration, and publication policy.

The benchmark is not a coding-capability benchmark and is not the methodology being tested. It does not prescribe one agent framework or enforcement mechanism.

## Authority

Repository authority is: current Git state; current repository documents and executable contracts; deterministic tests/configuration; approved bootstrap requirements not yet persisted; then historical conversation, which is non-authoritative.

## Provisional v0.1 domains

- **AUTH — Authority Integrity:** only the configured authoritative source controls an engineering decision when sources conflict.
- **MUT — Mutation Integrity:** overlapping shared-state mutation is prevented, serialized, isolated, or explicitly reconciled.
- **COMP — Completion Integrity:** lifecycle state is admitted only with required authority and evidence that remains valid.
- **REV — Review Integrity:** claimed review meets configured freshness, independence, and specialization requirements where applicable.
- **INV — Invalidation Integrity:** changed prerequisites invalidate the exact dependent assurance state that no longer holds.
- **REC — Reconstruction Integrity:** durable artifacts permit reconstruction after context loss without fabricated completion or stale evidence.

These domains are a provisional taxonomy, not claims of eternal or exhaustive categories.

## M1 scope

M1 implements contracts, typed core, deterministic functional/control oracles, a host-neutral runner, a non-intervening fake/reference adapter, exactly six seed scenarios, stored-evidence rescoring, deterministic tests, and independent review.

## Explicit non-goals

M1 does not implement hosted software, UI, model routing, an agent runtime, workflow DSL, database, task platform, telemetry/signature standard, Git/CI replacement, editor/GitHub integration, RBAC, incident database, leaderboard score, extra scenarios, or any real coding-agent/host adapter. It does not publish or push anything remotely.

