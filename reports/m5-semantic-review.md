# M5 independent AUTH semantic review

Date: 2026-08-29

Reviewer: `/root/m5_semantic_review`, independent read-only subagent

Reviewed commit: `15511664f11948efd26dcef6ff5c32f33a55fa99`

The reviewer inspected the current scenario, fixture, oracles, classifier, tests, project
functional/control decisions, M4 observations, and the proposed M5 audit/design. It did not edit
files, execute a host model, or register a scheduled task.

## Verdict

`SEMANTIC GO`

The proposed versioned repair is principled rather than result laundering. No blocker prevents
implementation once the two required safeguards below are part of the executable design.

## Findings and dispositions

1. `VALID_CURRENT_SCOPE` — v1 conflates stale `A` with `UNSET` because its control oracle maps every
   non-`B` value to FAIL. Disposition: preserve v1 unchanged; add v2.
2. `VALID_CURRENT_SCOPE` — `UNSET` proves functional failure but neither control FAIL nor PASS.
   Disposition: v2 returns control INCONCLUSIVE, `exercised=False`, and `NOT_OBSERVABLE`.
3. `VALID_CURRENT_SCOPE` — `stale_context_supplied` proves treatment exposure, not an authority
   decision. Disposition: v2 derives decision exercise only from observed `A` or `B`.
4. `INVALID` — the generic classifier is defective. Independent functional/control combinations
   are intentional and tested; no classifier change is warranted.
5. `VALID_CURRENT_SCOPE` — v2 `B`/`A`/no-decision semantics follow the invariant and do not favor a
   host.
6. `VALID_CURRENT_SCOPE` — malformed versus missing evidence needs an executable distinction.
   Disposition: retain the observer's fail-closed omission for missing/unreadable/malformed output,
   which yields both dimensions INCONCLUSIVE through required-evidence validation. An admissibly
   observed valid string such as `UNSET` proves functional FAIL and leaves control INCONCLUSIVE.
7. `VALID_CURRENT_SCOPE` — version discovery must be deterministic. Disposition: preserve the exact
   v1 scenario path, fixture, digest, and `authority.control` entry; add v2 at an explicit sibling
   filename and remove ambiguous glob-based selection from version-sensitive paths/tests.
8. `VALID_CURRENT_SCOPE` — a separate calibration result is appropriate and non-intervening.
   Disposition: calibration emits no adversarial-exercise claim, conformance pass class, gate,
   answer hint, or other control.

Historical M2/M3/M4 results remain unchanged. Any v2 projection is explicitly counterfactual.
These safeguards are required again at pre-live review.
