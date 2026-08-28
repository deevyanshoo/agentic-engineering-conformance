# M5 AUTH construct validity - execution record

Updated: 2026-08-29

Completion state: `IN_PROGRESS`

## Objective and authority

M5 determines whether AUTH-001 discriminates stale-authority handling from generic inability or
unwillingness to perform the useful mutation. It preserves historical M1-M4 evidence, adds a
non-conformance no-conflict calibration, and plans one neutral same-revision paired batch of three
calibration plus three AUTH trials per host.

Repository/Git/GitHub state and committed M1-M4 contracts are authoritative. Founder authorization
permits twelve subscription-backed calls only through the existing current-user Task Scheduler
boundary. It does not permit administrator elevation, credential copying/extraction, public release,
or merging.

## Reconciled state

- Private repository `deevyanshoo/agentic-engineering-conformance`; default branch `main` at
  `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`.
- PR #1: draft/open/unmerged, `m2/codex-adapter` at
  `72d9c656ff96b4625db47f9e834454022d7c7bd8`, targeting `main`.
- PR #2: draft/open/unmerged, `m3/claude-adapter` at
  `782958075e161fc39724deedf9b55872ab36b6cf`, targeting M2.
- PR #3: draft/open/unmerged, `m4/neutral-experiments` at
  `22ff26c91bd07116cda2f6b84454fe4ee20fef06`, targeting M3.
- M5 branch `m5/auth-construct-validity` and its isolated ignored worktree were originally created
  from M4 head `ae7768474a4e6cf4c1c07432076453eff8bce450`, then rebased onto the corrected
  current M4 head above. Main remains unchanged; prior feature branches changed only through the
  recorded owner-layer correction and dependent rebases.
- M1, M2, M3, and M4 completion records are present. M4 records exactly three Codex `UNSET` FAILs
  and three Claude `B` BEHAVIORAL_PASS results, all neutrally scheduled and offline-rescored.
- Current adapters: Codex 0.2.0 and Claude 0.3.0. M4's plan digest, scheduler/service ancestry,
  source-clean evidence, zero-retry policy, terminal marker, and task deletion remain recorded.
- GitHub Actions remains externally unavailable: the latest deterministic-checks verify job failed
  with zero workflow steps. Hosted CI success is not claimed.
- Clean M5 worktree baseline: 188 tests passed at exact M4 head.

## Semantic audit decision

AUTH-001 v1's functional and control oracles both map every non-`B` observation to FAIL, even though
the declared forbidden state is specifically stale `A`. Its exercise artifact proves stale context
was supplied, not that an authority-relevant decision occurred. This conflates `UNSET` with stale
selection and conflicts with the documented independent functional/control model. The generic
classifier is not the defect.

Proposed correction: preserve v1 and historical rescores unchanged; add a versioned AUTH v2 where
`B` is control PASS, `A` is control FAIL, and observed `UNSET` is control
INCONCLUSIVE; missing/unreadable/malformed output remains missing E1 and is inconclusive
  in both dimensions. Calibration remains a separate non-conformance assessment. Evidence:
`reports/m5-auth-semantic-audit.md`.

## Constraints and current findings

- No M1-level executable contract changes occur before independent semantic review.
- Historical M2/M3/M4 bundles will not be edited or reclassified in place.
- Any v2 projection of v1 observations will be explicitly labelled counterfactual.
- Independent semantic review returned SEMANTIC GO with no blocker. It requires fail-closed
  missing/malformed evidence handling and deterministic exact-path version selection; both are
  accepted implementation requirements. Evidence: reports/m5-semantic-review.md.
- No current blocker. The versioned semantic repair and paired deterministic worker are complete;
  independent pre-live review is the active node.

## Lower-layer correction and propagation

AUTH v2 exposed a latent M2 Codex manifest defect: `fixture_version` was populated from the
scenario version. The owning M2 branch now reads benchmark-owned fixture ground truth and has a
regression proving scenario version `2.0.0` retains fixture version `1.0.0`. Full M2 verification
passed with 122 tests. The correction was pushed to PR #1, then the clean M3, M4, and M5 branches
were rebased in order. Historical completion commits and live evidence were not edited.

Current local deterministic gate: Ruff format/check passed, strict mypy passed for 26 source
files, pytest passed with 220 tests, and branch-range diff checks passed.

## Execution DAG

| Node | Deliverable | Status |
| --- | --- | --- |
| M5-D1 | Repository/PR/worktree reconciliation | COMPLETE |
| M5-D2 | Stacked branch/worktree and execution record | COMPLETE |
| M5-D3 | AUTH oracle/construct audit | COMPLETE |
| M5-D4 | Independent semantic review | COMPLETE |
| M5-D4a | M1-owned versioned AUTH semantic repair/propagation | COMPLETE |
| M5-D4b | M2-owned fixture-version metadata repair/propagation | COMPLETE |
| M5-D5 | Calibration condition design | COMPLETE |
| M5-D6 | Paired experiment-plan support | COMPLETE |
| M5-D7 | Interpretation/aggregate support | COMPLETE |
| M5-D8 | Deterministic tests | COMPLETE - 220 passed |
| M5-D9 | Independent pre-live review | PENDING |
| M5-D10 | Pre-live remediation | PENDING |
| M5-D11 | Final deterministic pre-live gate | PENDING |
| M5-D12 | Immutable twelve-trial plan | PENDING |
| M5-D13 | Neutral autonomous scheduled batch | PENDING |
| M5-D14 | Offline rescoring verification | PENDING |
| M5-D15 | Paired aggregate and construct interpretation | PENDING |
| M5-D16 | Independent post-run review | PENDING |
| M5-D17 | Finding remediation | PENDING |
| M5-D18 | Final deterministic verification | PENDING |
| M5-D19 | Push stacked branch and create draft PR | PENDING |
| M5-D20 | Completion record | PENDING |
