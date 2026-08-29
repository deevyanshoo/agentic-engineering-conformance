# Charter and scope

Agentic Engineering Conformance evaluates whether a declared engineering stack around a coding agent preserves its claimed engineering-control invariants under adversarial, interrupted, conflicting, or changing conditions. The unit under test may include a model, host, repository instructions, workflow, tools, isolation strategy, CI/review configuration, and publication policy.

The benchmark is not a coding-capability benchmark and is not the methodology being tested. It does not prescribe one agent framework or enforcement mechanism.

## Authority

Repository authority is: current Git state; current repository documents and executable contracts; deterministic tests/configuration; approved requirements not yet persisted; then historical conversation, which is non-authoritative. Versioned scenario and evidence records remain authoritative for their historical experiment even when a later contract corrects future semantics.

## Provisional v0.1 domains

- **AUTH - Authority Integrity:** only the configured authoritative source controls an engineering decision when sources conflict.
- **MUT - Mutation Integrity:** overlapping shared-state mutation is prevented, serialized, isolated, or explicitly reconciled.
- **COMP - Completion Integrity:** lifecycle state is admitted only with required authority and evidence that remains valid.
- **REV - Review Integrity:** claimed review meets configured freshness, independence, and specialization requirements where applicable.
- **INV - Invalidation Integrity:** changed prerequisites invalidate the exact dependent assurance state that no longer holds.
- **REC - Reconstruction Integrity:** durable artifacts permit reconstruction after context loss without fabricated completion or stale evidence.

These domains are a provisional taxonomy, not eternal or exhaustive categories.

## v0.1 alpha scope

- typed scenario, evidence, run, result, calibration, and experiment-plan contracts;
- deterministic functional/control oracles and six synthetic reference scenarios;
- host-neutral runner and non-intervening adapter boundary;
- deterministic reference adapter covering all classifications and offline rescoring;
- Codex and Claude Code AUTH-001 adapters;
- AUTH-001 v1 historical replay, v2 no-decision semantics, and no-conflict calibration; and
+- experimental digest-bound neutral execution through current-user Windows Task Scheduler.
+
+Only AUTH has real-host integration evidence. Reference scenarios for the other five domains test benchmark architecture, not real-host conformance.
+
+## Explicit non-goals
+
+The alpha does not implement hosted software, a UI/dashboard, model router, custom agent runtime, workflow DSL, database, task platform, telemetry/signature standard, Git or CI replacement, editor/GitHub integration, RBAC, incident database, composite score, leaderboard, certification program, or additional real-host adapter.
+
+It does not require chain-of-thought, standardize the wider ecosystem, rank control mechanisms, or infer general host quality from small experiments.
+
+## Publication boundary
+
+Source publication does not convert experimental observations into certification. Public artifacts follow [the evidence policy](evidence-policy.md), claims follow [the claim register](claims.md), and release operations require a separately authorized publication gate.
+'@
$adr=@'
# ADR 0002: Public alpha policy

Status: accepted for provisional `v0.1.0-alpha.1`. Date: 2026-08-29.

1. **Single license boundary:** Apache-2.0 covers code, schemas, scenarios, synthetic fixtures, authored benchmark data, documentation, and contributions.
2. **Public evidence minimization:** publish deterministic contracts, sanitized manifests/aggregates, methodology, and review evidence; exclude raw prose-bearing diagnostics, credentials, private reasoning, and unnecessary machine identifiers.
3. **Historical replay:** preserve AUTH-001 v1 and M1-M5 evidence; later semantic contracts are versioned and counterfactual rescores are labeled.
4. **No ranking:** small real-host experiments are exact-run integration/construct evidence only.
5. **Contributor gate:** ordinary contributions require only local deterministic checks, never a paid model account.
6. **CI honesty:** retain the deterministic workflow but claim hosted CI only after repository steps actually run; local and clean-clone evidence remains explicit.
7. **Publication authority:** `PUBLIC_ALPHA_READY` does not authorize merges, a visibility change, a tag, or a release.

Consequences: public readers can reproduce the reference framework without credentials; the alpha remains candid about Windows-only neutral execution, sparse host evidence, and taxonomy uncertainty.