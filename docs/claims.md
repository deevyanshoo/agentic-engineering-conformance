# Public claim register

This register defines the strongest claims supported by CoderPolice. A passing result is scoped to its declared scenario, stack configuration, and admissible evidence; it is not a general certification.

## What we claim

- A host-neutral five-method adapter abstraction is exercised by the deterministic reference adapter and independently implemented by OpenAI Codex and Claude Code adapters.
- Six synthetic reference scenarios cover the provisional AUTH, MUT, COMP, REV, INV, and REC domains with deterministic functional and control oracles.
- The result model separates functional success from control preservation and distinguishes guarded from merely behavioral passes.
- Scenario ground truth is benchmark-owned; externally observed deterministic E1 evidence is preferred, and E4 agent assertions cannot satisfy a deterministic oracle alone.
- Stored evidence can be validated and rescored without executing the adapter or host again.
- AUTH-001 versioning preserves historical v1 replay while v2 distinguishes stale selection from an observed no-decision state.
- A separate no-conflict calibration can test the useful mutation without calling its outcome AUTH conformance.
- A digest-bound worker can be launched through current-user, least-privilege Windows Task Scheduler and records best-effort ancestry, source binding, outcomes, offline rescores, and task cleanup.
- M1-M6 development included independent read-only reviews whose findings and dispositions remain in repository reports.

## What remains experimental

- Completeness and construct validity of the six-domain taxonomy.
- AUTH construct validity across real hosts and configurations.
- Portability and neutrality of the Windows Task Scheduler approach beyond the recorded current-user Windows context.
- Stochastic reliability, repeatability at useful sample sizes, and cross-host comparative performance.
- Effectiveness of any particular workflow, hook set, methodology, or control mechanism.
- Real-host support for MUT, COMP, REV, INV, and REC; current real adapters cover AUTH-001 only.
- Security of the host, operating system, credentials, network, or supply chain.

## What we do not claim

- The first agentic engineering control plane, evidence-gated coding workflow, proof-of-done system, task DAG, independent agent review, dependency invalidation system, incident-to-eval system, durable agent-state system, or multi-agent orchestrator.
- A new Agent Skills, telemetry, trace, provenance, evidence-signature, Git, CI, or workflow standard.
- Codex versus Claude superiority, a winner, pass-rate advantage, model ranking, composite score, or leaderboard.
- Production security certification, a complete agent-safety framework, or proof that a stack is safe outside the exact declared invariant.
- Validation of all six domains against real hosts.
- That a reference-adapter result predicts a stochastic host result.
- Novelty, trademark clearance, or legal priority for the product name `CoderPolice` or the technical descriptor `Agentic Engineering Conformance`.

The candidate contribution is a vendor-neutral adversarial conformance framework for engineering-control guarantees around coding-agent stacks. That remains a research hypothesis, not a novelty claim. See [prior art](prior-art.md).
