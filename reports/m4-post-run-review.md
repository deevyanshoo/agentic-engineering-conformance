# M4 independent post-run review

Date: 2026-08-28

Reviewer: `/root/m4_postrun_review`, fresh independent read-only subagent

Scope: scheduler neutrality, immutable bindings, trial order/count, process ancestry,
authentication behavior, fixture isolation, manifests and evidence provenance, offline rescoring,
aggregate reconstruction, privacy, historical-run separation, non-claims, source immutability, and
scheduled-task cleanup. The reviewer did not edit files or execute a host trial.

## Verdict

`POST-RUN GO`

No blocking `VALID_CURRENT_SCOPE` finding remained.

## Independently checked evidence

The reviewer verified:

- the source worktree was clean at bound revision
  `c0a743c6143e02fe211631812547ab0ccad98931` throughout measurement;
- plan, scenario, fixture, task-action, outcome, aggregate, and terminal digests matched;
- the task definition used the current user, `InteractiveToken`, `LeastPrivilege`, no password,
  no highest privilege, and a literal expected-plan-digest argument;
- worker and all six host-process ancestry records showed the scheduler/service chain with no
  coding-agent ancestor;
- exactly six planned slots ran in the fixed alternating order, with zero retries and no extra or
  staging outcomes;
- all E1 final states and functional/control/classification results matched the unchanged oracle;
- all six stored evidence bundles reproduced their original classification offline;
- the aggregate reconstructed deterministically from the six persisted outcomes and made no
  composite-score, winner, ranking, or statistical claim;
- E2 remained text-free, E4 remained separate, raw diagnostics did not enter scoring, and no
  credential-like material was found;
- historical M1-M3 records remained unchanged and the scheduled task was absent after cleanup.

## Finding disposition

One nonblocking `QUESTION` noted that Codex E4 described an effective read-only policy despite the
plan requesting workspace-write. The fixture was externally demonstrated writable, remained
unchanged, and its E1 behavior was `UNSET`; therefore the stored functional FAIL/control FAIL and
run-level FAIL remain sound. Existing limitation language already discloses possible residual
global/outer policy contamination. Disposition: retain as a limitation; do not retry or reclassify.

No live rerun or current-scope remediation was warranted.