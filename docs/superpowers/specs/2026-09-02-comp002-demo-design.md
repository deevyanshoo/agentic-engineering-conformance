# COMP-002 Terminal Demo Design

## Goal

Provide one short, cross-platform command that explains COMP-002 using the existing
deterministic reference contract, Runner, evidence model, completion oracles, and offline
rescoring.

## Boundaries

- Keep `scenarios/completion/COMP-002/scenario.json`, `completion.functional`,
  `completion.control`, and generic classification unchanged.
- Run no real host and make no Codex, Claude Code, empirical-validation, blocking, or security
  claim.
- Leave no evidence file behind.
- Use plain text without ANSI styling, emoji, or em dashes.

## Design

Add `agentic_conformance.demo_comp002` as a presentation module. It loads COMP-002, runs two
deterministic cases through `Runner(seed_oracle_registry())`, serializes and restores each
evidence bundle in memory, and verifies that `rescore` exactly equals the original result.
Presentation fields are derived from the scenario, evidence artifacts, and `RunResult` values.

CASE 1 uses the existing `guarded_pass` ReferenceAdapter behavior: source A verification remains,
candidate B is functional, completion for B is not verified, and the exercised stale-evidence
condition is detected and recovered. The unchanged model produces `GUARDED_PASS`.

CASE 2 uses one narrowly scoped ReferenceAdapter mode, `current_verification`, for COMP-002. It
emits a passing verifier record bound to B and a verified completion state bound to B. It emits no
adversarial exercise or control event. The unchanged model therefore produces
`BEHAVIORAL_PASS`: functional correctness and the current-evidence invariant hold, but an
exercised guard is not proven.

The public command is:

```shell
python -m agentic_conformance.demo_comp002
```

## Testing

Focused tests will prove scenario selection, both evidence bindings, Runner/oracle provenance,
original-versus-offline-rescore equality, the semantic difference between control responses and
classifications, truthful synthetic framing, and absence of real-host claims. The full requested
format, lint, type, test, and diff checks remain release gates.
