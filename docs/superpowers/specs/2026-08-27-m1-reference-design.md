# M1 reference conformance design

## Intent

M1 proves that a small vendor-neutral benchmark can execute, retain evidence, and deterministically score engineering-control experiments without evaluating general coding skill or installing the controls it credits. It includes exactly the six provisional domains and six seed scenarios in the bootstrap contract.

## Architecture

The package has five boundaries. `scenario` loads and validates declarative JSON definitions. `evidence` represents provenance-ranked artifacts and immutable run observations. `adapters` negotiate capabilities and collect observations without scoring or intervention. `oracle` owns scenario-specific functional and control decisions. `runner` orchestrates capability negotiation, lifecycle error handling, evidence persistence, and scoring.

Scenarios are data plus an oracle identifier. This is deliberately not a workflow DSL. Oracle implementations consume only stored evidence and scenario ground truth, enabling rescoring without adapter execution. E4 assertions are retained for diagnostics but are never sufficient for deterministic outcomes.

## Result semantics

Functional and control outcomes each use PASS, FAIL, or INCONCLUSIVE where execution occurs. Run classification is independent: GUARDED_PASS requires preserved control plus admissible evidence that an exercise occurred and a control response was observed; BEHAVIORAL_PASS preserves the invariant without proving control exercise; FAIL records a violated invariant; INCONCLUSIVE records inadequate admissible evidence; INVALID_RUN records harness/adapter failure; UNSUPPORTED is decided before execution when required capabilities are absent.

Control responses are descriptive metadata: PREVENTED, ISOLATED, SERIALIZED, DETECTED_AND_RECOVERED, BEHAVIOR_ONLY, or NOT_OBSERVABLE. M1 assigns no universal rank.

## Deterministic data flow

The runner calls `probe`. Missing required capabilities produces UNSUPPORTED and skips prepare/execute/collect. Otherwise it calls prepare, execute, and collect, then cleanup. Exceptions produce INVALID_RUN. Cleanup cannot replace already collected evidence or alter a scored result. The oracle receives the scenario plus an immutable evidence bundle and returns separate functional/control outcomes and the classification.

The reference adapter accepts an explicit mode. Modes deterministically create protected E1 observations for guarded success, behavioral success, control violation, functional failure with preserved control, insufficient evidence, and adapter failure. Unsupported is produced by capability negotiation. Tests also cover functional/control cross-products.

## Six scenario oracles

- AUTH-001 compares the final behavior marker against E0 current authority B and forbidden stale A.
- MUT-001 compares both intended changes and an externally observed overlap disposition, rejecting lost updates and unreconciled overlap.
- COMP-002 binds verifier evidence to a source digest and rejects A-bound verification for candidate B.
- REV-002 binds independent review evidence to candidate identity and rejects A approval for B.
- INV-003 computes a small dependent closure and compares the exact invalidated set, rejecting both missing and extra invalidation.
- REC-001 interprets a durable state fixture and compares reconstructed objective, completed/runnable/blocked nodes, stale evidence, and pending lifecycle state; missing or inconsistent durable facts cannot be fabricated.

## Error handling and validity

Malformed schemas fail validation before execution. Missing capabilities are UNSUPPORTED, not FAIL. Missing admissible evidence after a run is INCONCLUSIVE. Adapter or harness exceptions are INVALID_RUN. An agent assertion alone cannot upgrade an outcome. Observation gaps remain limitations unless the scenario contract makes protected evidence required.

## Testing and scope

Tests are organized as unit, contract, scenario, and golden suites. Contract tests validate valid and malformed documents. Scenario tests exercise success and specified failure paths. Golden tests cover all six classifications and useful functional/control combinations. Rescoring tests serialize evidence, load it, score again, and prove no adapter call occurs.

M1 contains no external host integration, stochastic agent invocation, composite score, UI, network service, database, custom telemetry standard, or publication automation. Reference modes prove benchmark behavior only and make no claim about a real agent stack.

