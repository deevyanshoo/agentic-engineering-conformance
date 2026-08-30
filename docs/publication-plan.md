# Public alpha integration and publication plan

Status: prepared only. Founder authorization required before any operation in the execution section. The repository remains private; no merge, tag, release, or visibility change has occurred.

## Verified private stack

Observed 2026-08-29:

| PR | Head branch | Verified head | Current base | State |
| --- | --- | --- | --- | --- |
| PR #1 | `m2/codex-adapter` | `72d9c656ff96b4625db47f9e834454022d7c7bd8` | `main` | draft, open, unmerged |
| PR #2 | `m3/claude-adapter` | `782958075e161fc39724deedf9b55872ab36b6cf` | `m2/codex-adapter` | draft, open, unmerged |
| PR #3 | `m4/neutral-experiments` | `3bcc4c458d6e49a4218454be6b68f5a7ffb82e49` | `m3/claude-adapter` | draft, open, unmerged |
| PR #4 | `m5/auth-construct-validity` | `9eee1d372134f19dbfb175b05125caae857c5a45` | `m4/neutral-experiments` | draft, open, unmerged |
| PR #5 | `m6/public-alpha-readiness` | `fe750149d9b1d8d672ced0d1cedeb7e5a65caaac` at PR creation; final required head is the M6 completion SHA | `m5/auth-construct-validity` | draft, open, unmerged |

Each listed milestone head is an ancestor of the next. `origin/main` remains `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`. PR #5 will advance only through reviewed M6 closure commits; its exact final head must equal the launch-candidate SHA in the completion record and final handoff before integration begins.

## Invariants

- Integration order is exactly `#1 -> #2 -> #3 -> #4 -> #5`.
- No auto-merge. Each merge is an explicit founder-authorized operation after a fresh head/base/diff check.
- No squash, rebase merge, force push, or history rewrite. Use normal merge commits to retain milestone and lower-layer correction provenance.
- Do not delete source branches until the release is complete and provenance has been rechecked.
- A downstream PR is retargeted to `main` only after its direct dependency is verified present in `origin/main`.
- Any unexpected head, base, diff, conflict, visibility, audit, or verification result stops the sequence.

## Founder-authorized integration sequence

For every step: fetch, verify the recorded expected head, inspect the PR range/name-status, confirm deterministic evidence remains applicable, mark that one PR ready, merge with the normal merge method, fetch again, and prove the PR head is an ancestor of the new `origin/main`.

1. Verify `origin/main` still contains the M1 baseline and PR #1 head is exact. Mark PR #1 ready and merge it into `main` with a merge commit.
2. Retarget PR #2 from M2 to `main`. Verify the remaining diff is exactly M3 (`72d9c656...78295807`), then mark ready and merge. Verify PR #2 head is in `origin/main`.
3. Retarget PR #3 from M3 to `main`. Verify the remaining diff is exactly corrected M4 (`78295807...3bcc4c45`), then mark ready and merge. Verify PR #3 head is in `origin/main`.
4. Retarget PR #4 from M4 to `main`. Verify the remaining diff is exactly M5 (`3bcc4c45...9eee1d37`) and preserves the M4 path-correction propagation merge, then mark ready and merge. Verify PR #4 head is in `origin/main`.
5. Retarget PR #5 from M5 to `main`. Verify its head exactly equals the recorded M6 launch-candidate SHA and its remaining diff is exactly `9eee1d37...<M6 completion SHA>`, then mark ready and merge. Verify that head is in `origin/main`.
6. From a fresh clone of the integrated `main`, rerun Ruff format/check, strict mypy, full pytest/schema contracts, the deterministic reference/rescore example, branch diff checks, and current-tree plus reachable-history privacy/proprietary scans. Stop on any difference.

GitHub-created merge commit SHAs cannot be predicted in this private plan; each observed merge SHA becomes authoritative only after its parentage and included milestone head are verified.

## Founder-authorized public release sequence

Only after the five integrations and post-integration gate pass:

1. Change repository visibility from PRIVATE to PUBLIC using GitHub's explicit visibility-change confirmation.
2. Manually dispatch exactly one `ci.yml` deterministic run on integrated `main`. Claim hosted CI success only if repository steps execute and pass. If external availability still prevents execution, record that limitation without retry loops or a fabricated status and return to the founder for the release decision.
3. Recheck public repository name, license display, default branch, README links, tags, releases, and sanitized tracked artifacts.
4. Create annotated tag `v0.1.0-alpha.1` at the exact verified integrated `main` head and push that tag.
5. Create a GitHub prerelease from the committed draft notes, verify it points to the exact tag, and retain all alpha/non-claim language.

The deterministic workflow never receives model credentials and never runs live Codex or Claude trials. No package-registry publication is part of this release plan.

## Actions reserved for founder authorization

- marking PRs #1-#5 ready and merging them;
- retargeting dependent PRs as part of that integration sequence;
- changing repository visibility to PUBLIC;
- deciding whether to proceed if post-public hosted Actions remains externally unavailable;
- creating/pushing `v0.1.0-alpha.1`; and
- creating the public GitHub prerelease.