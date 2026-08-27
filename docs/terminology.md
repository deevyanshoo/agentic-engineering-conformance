# Terminology

**Stack under test:** the declared model/host/repository/workflow/tooling/configuration combination being evaluated.

**Scenario:** versioned declarative setup, adversarial condition, invariant, evidence contract, policies, and oracle identifiers.

**Functional outcome:** whether the requested useful engineering task succeeded: PASS, FAIL, or INCONCLUSIVE.

**Control outcome:** whether the engineering invariant was preserved: PASS, FAIL, or INCONCLUSIVE.

**Run classification:** GUARDED_PASS, BEHAVIORAL_PASS, FAIL, INCONCLUSIVE, INVALID_RUN, or UNSUPPORTED. GUARDED_PASS requires observed exercise and protection/containment; BEHAVIORAL_PASS records intact behavior without proof that a control was exercised. UNSUPPORTED is a pre-run capability outcome. INVALID_RUN denotes experiment failure rather than stack conformance.

**Control response:** descriptive metadata: PREVENTED, ISOLATED, SERIALIZED, DETECTED_AND_RECOVERED, BEHAVIOR_ONLY, or NOT_OBSERVABLE. v0.1 does not rank these universally.

**Candidate identity:** deterministic digest/version of the state being verified or reviewed.

**Admissible evidence:** evidence that meets a scenario's required provenance and binding rules. An E4 agent assertion alone is never admissible for deterministic success.

**Rescoring:** applying a current scenario oracle to previously stored scenario ground truth and evidence without executing an adapter again.

**Observation mode:** BLACK_BOX uses externally deterministic state; PASSIVE_INSTRUMENTED may record host events but cannot change behavior.

