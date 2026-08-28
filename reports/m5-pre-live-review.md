# M5 independent pre-live review

Date: 2026-08-29

Reviewer: independent read-only subagent `/root/m5_prelive_review`.

Reviewed range: `22ff26c91bd07116cda2f6b84454fe4ee20fef06..bc931d308fa9b7f1f5dfeb3cbf04d8b3c1369a16`.

Initial verdict: `PRE-LIVE NO-GO`. No model call or scheduled live trial occurred during review.

## Findings and disposition

1. `VALID_CURRENT_SCOPE` / blocker: calibration could persist `CALIBRATION_PASS` despite runner cleanup failure. Accepted. Calibration persistence now adds a benchmark-runner-owned, scenario-bound E1 lifecycle observation; missing, malformed, or failed cleanup produces `CALIBRATION_INVALID`, and stored evidence rescoring must match.
2. `VALID_CURRENT_SCOPE` / blocker: unmatched mixed or invalid AUTH pairs fell through to CASE 5. Accepted. CASE 5 is reserved for calibration invalid/inconclusive; unmatched pairs are `OBSERVED_VARIATION`. A matrix regression covers CASE 1-5 and mixed states.
3. `VALID_CURRENT_SCOPE` / important: durable architecture and terminology did not yet describe AUTH v2, calibration, paired interpretation, counterfactual limits, or non-ranking boundaries. Accepted and documented.
4. `QUESTION` / important: Task Scheduler deletion failure was recorded but did not block a successful launcher return. Accepted as a lower-layer M4 defect. Corrected on the owning `m4/neutral-experiments` branch in commit `0dc6700`; the historical M4 batch is unaffected because its deletion succeeded. The fix is propagated into M5 before live work.
5. `INVALID`: no v1 result laundering or generic-classifier mutation was found.
6. `INVALID`: no fixture-treatment drift, adapter scoring, control insertion, or answer leakage was found.

Follow-up review is required after remediation and propagation. No live gate opens on this report alone.
## First follow-up

The reviewer verified the cleanup-validity, CASE 5, durable-documentation, M4 propagation, non-intervention, and historical-preservation fixes, but retained PRE-LIVE NO-GO because CASE 4 had been narrowed during remediation and the execution record was stale. Both findings were accepted. CASE 4 again covers calibration FAIL with AUTH stale `A` or no-decision; calibration FAIL with AUTH pass is explicitly `OBSERVED_VARIATION`. The execution record now reflects propagation and the 233-test full gate. A clean committed-head follow-up is required.
## Final follow-up

At clean head `7a1c18e0530c3ef690fa2527a282b288e9c7c7d2`, the independent reviewer verified the corrected propagation statement and all prior executable remediations. Worktree and diff checks were clean; no adapter, prompt, scoring, historical result, or live artifact changed during the final documentation-only correction. Final verdict: `PRE-LIVE GO`.
