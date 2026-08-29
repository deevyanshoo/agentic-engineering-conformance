# Contributing scenarios

A scenario is a small adversarial experiment, not a workflow DSL or narrative prompt collection.

## Proposal checklist

1. Name one protected engineering object and one falsifiable invariant.
2. Explain why the scenario belongs to an existing provisional domain.
3. Define useful functional success separately from control preservation.
4. Make required and forbidden states objectively distinguishable without an LLM judge.
5. State the exercise condition and what evidence proves it occurred.
6. Prefer benchmark-owned E0 and externally observed E1; explain every E2/E3 dependency.
7. Ensure E4 assertions cannot determine the score.
8. Declare required capabilities so missing support becomes `UNSUPPORTED`, not `FAIL`.
9. Include limitations, provenance, network/human/trial policy, and synthetic fixture licensing.

## Files and validation

Place a versioned `scenario.json` under `scenarios/<domain>/<ID>/` and its deterministic fixture under `fixtures/`. Validate against `schemas/scenario.schema.json`, add oracle code only to the scenario-owned oracle layer, and cover malformed input, missing evidence, success, violation, and inconclusive paths.

If semantics change, add a new versioned definition. Do not edit an older contract so stored historical evidence silently changes meaning. Tests must prove old-version replay and new-version selection.

Run the deterministic contributor gate in [CONTRIBUTING.md](../CONTRIBUTING.md). A scenario proposal does not require a live host trial.