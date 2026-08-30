# M6 Public Alpha Readiness completion

Date: 2026-08-29

Completion state: `PUBLIC_ALPHA_READY`

This state means the private repository is prepared for a founder-authorized integration and public alpha release. It does not mean merged, public, tagged, released, or published.

## Authority and history

- M1-M5 completion/history remains reconstructable; the terminal M5 batch is unchanged and distinct from the M6 successor.
- AUTH-001 v1 remains replayable; v2 and calibration semantics are versioned and public.
- Draft PRs #1-#5 remain open and unmerged. M6 PR #5 targets M5. `main` remains the M1/post-remote baseline.
- Repository visibility remains PRIVATE. No local/remote tag or GitHub release exists.

## Launch-validation evidence

The separate M6 successor bound AUTH-001 v2 plus calibration to committed revision `ae83c522c5ef5cd8db85d4563fe5a6357c084272` and plan digest `sha256:2972849625c9f29f4a9d060b1330b9811a691a4a668f078ac65cbf7156ca83cd`. Task Scheduler executed exactly twelve zero-retry BLACK_BOX slots; all twelve offline rescores matched, source remained unchanged, service ancestry was observed, and the one-time task was deleted.

The exact run-specific aggregate is intentionally noncomparative: the recorded Codex configuration produced three calibration `UNSET` outcomes and three paired AUTH v2 functional-fail/control-inconclusive outcomes (Case 4, construct-confounded); the recorded Claude configuration produced three calibration `B` outcomes and three paired AUTH v2 behavioral passes with `B` (Case 1, no exercised guard proven). N=3 per condition supports no ranking, statistical, security, or global-conformance claim.

## Public hardening

- Apache-2.0 applies repository-wide to project-authored code, schemas, scenarios, fixtures, data, and documentation.
- Exact-name GitHub/PyPI checks found no blocking collision; broader terminology is used elsewhere and `AEC` is not promoted as unique. This is not legal clearance.
- Current-tree and reachable-history audits found no secret, credential assignment, proprietary sentinel, tracked raw transcript/JSONL/log, suspicious artifact, oversized blob, current absolute home path, or current machine/user principal.
- Harmless historical M2/M3 executable paths and M4 scheduler principal remain only in old commits; current derivatives are sanitized/labeled and no destructive rewrite is justified.
- README, claim/non-claim register, prior art, evidence/privacy, licensing, contribution, conduct, security, issue/PR guidance, CI strategy, roadmap, and draft release notes are launch-facing.

## Independent review

- Fresh engineering reviewer: `ENGINEERING LAUNCH GO`, no blocking finding.
- Fresh public/claims reviewer: initial NO-GO with three valid blockers; all were remediated, regression-tested, audit-disposed, and independently rechecked as `PUBLIC/CLAIMS LAUNCH GO`.
- All blocking `VALID_CURRENT_SCOPE` findings are resolved.

## Verification

Pre-record launch candidate `7fc7d3d1589457e0655f1bfcafebf4264c08c8b1`:

- `python -m ruff format --check .`: PASS, 121 files;
- `python -m ruff check .`: PASS;
- `python -m mypy --strict src`: PASS, 27 source files;
- `python -m pytest -q`: PASS, 243 tests in 46.08 seconds;
- worktree and M5-to-M6 `git diff --check`: PASS;
- deterministic reference evidence/offline rescore: PASS; and
- fresh-clone install and deterministic suite: PASS (the exact completion-record head is rechecked after this record commit).

The checked-in workflow contains the same deterministic gate, no live hosts or secrets, and a manual dispatch. Hosted CI success is not claimed while the private account restriction prevents repository steps.

## Publication boundary

`docs/publication-plan.md` is the authoritative prepared order: PR #1 -> #2 -> #3 -> #4 -> #5, normal merge commits, retarget and ancestry checks, post-integration clean-clone/audit, public visibility, one deterministic Actions probe, then the `v0.1.0-alpha.1` tag/prerelease. Founder authorization is required for every merge, the visibility change, the tag, and the release.