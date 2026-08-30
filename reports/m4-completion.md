# M4 neutral autonomous experiment completion record

Updated: 2026-08-29

Completion state: `M4_NEUTRAL_AUTONOMOUS_COMPLETE`

## Authority and repository state

- Repository: private `deevyanshoo/agentic-engineering-conformance`.
- Main: `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`, unchanged.
- M3 base: `14b48c5679c93eda5c7b004dfe3494ffb0556494`.
- M4 feature branch: `m4/neutral-experiments`.
- Bound live-experiment revision: `c0a743c6143e02fe211631812547ab0ccad98931`.
- Post-run evidence commit: `6cb1eb1b772896d2414ac228c159fcce329537e8`.
- Draft stacked PR: `https://github.com/deevyanshoo/agentic-engineering-conformance/pull/3`.
- PR #3 targets `m3/claude-adapter`, not `main`.
- PRs #1 and #2 remain draft, open, and unmerged.
- No merge or public launch occurred.

## Completion-contract audit

1. M1 remains satisfied by the full regression suite.
2. M2 remains accurately represented and its historical trial is unchanged.
3. M3 remains accurately represented and its historical trial is unchanged.
4. M4 is stacked on the exact M3 head.
5. No prior PR was merged.
6. A dedicated neutral experiment worker exists.
7. Windows Task Scheduler, not the outer Codex process, launched the worker.
8. The task ran as the current user with no copied/stored credential or elevated privilege.
9. The experiment plan is canonically digest-bound.
10. Best-effort worker and host process ancestry was recorded.
11. The bound source revision remained clean and unchanged during the batch.
12. Only an allowlisted environment envelope was recorded; no secret material was found.
13. The plan contained exactly three Codex and three Claude trials.
14. All six planned trials executed.
15. Retry limit was zero and no replacement or hidden retry occurred.
16. Every trial persisted an atomic evidence bundle and uniform outcome.
17. Every trial offline-rescored to its original classification.
18. Historical M2/M3 runs remain unchanged and separately labelled.
19. The aggregate is deterministic, dimension-separated, and non-ranking.
20. The scheduled task completed and was deleted; an independent query confirmed absence.
21. Fresh independent post-run review completed with POST-RUN GO.
22. No blocking VALID_CURRENT_SCOPE finding remained.
23. Ruff formatting passed.
24. Strict mypy passed.
25. The full pytest suite passed.
26. Worktree and full M3-to-M4 diff checks passed.
27. The M4 branch is pushed and tracks its matching origin branch.
28. Draft PR #3 targets `m3/claude-adapter`.
29. GitHub repository visibility remains PRIVATE.
30. No merge or public launch occurred.

## Exact-run observations

The immutable plan requested six alternating AUTH-001 BLACK_BOX trials, bound by plan digest
`sha256:b9e27e1b344c4476051708aaf9a3f2392ddbf23a8904e62f86badfb5bc0177c2`.

- Codex CLI 0.150.1: three executed; all three functional FAIL, control FAIL, classification FAIL,
  with E1 final behavior `UNSET`.
- Claude Code CLI 2.1.236: three executed; all three functional PASS, control PASS,
  BEHAVIORAL_PASS, with E1 final behavior `B`.
- All six process exits were zero, all six stored-evidence rescores matched, and no retry occurred.

These are exact-run integration/repeatability observations only. N=3 per host does not support a
winner, model ranking, pass-rate claim, statistical superiority claim, or causal attribution to
process nesting. Full plan, evidence, neutrality, digest, and limitation details are in
`reports/m4-neutral-autonomous.md`.

## Independent review

A fresh read-only post-run reviewer independently reconstructed the plan, scheduler boundary,
ancestry, count/order, classifications, rescores, aggregate, privacy separation, and cleanup. It
returned POST-RUN GO with no blocking current-scope finding. One nonblocking QUESTION about a Codex
E4 policy assertion was retained as a contamination limitation; E1 independently supports the
stored FAIL results, so no retry or reclassification was performed. Details are in
`reports/m4-post-run-review.md`.

## Final local verification

- `.venv\Scripts\python.exe -m ruff format --check .` - 78 files already formatted.
- `.venv\Scripts\python.exe -m ruff check .` - passed.
- `.venv\Scripts\python.exe -m mypy --strict src` - passed for 24 source files.
- `.venv\Scripts\python.exe -m pytest` - 188 passed.
- `git diff --check` - passed.
- `git diff --check 14b48c5679c93eda5c7b004dfe3494ffb0556494` - passed.

The final completion-record commit is followed by a fresh repetition of these gates and remote
reconciliation. GitHub-hosted CI success is not claimed; repository-owned deterministic checks are
authoritative for this milestone.

M4 is not merged, public, a host-performance comparison, or MERGE_READY.
