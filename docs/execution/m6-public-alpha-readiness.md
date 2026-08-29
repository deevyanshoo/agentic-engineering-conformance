# M6 Public Alpha Readiness - execution record

Updated: 2026-08-29

Completion state: `IN_PROGRESS`

## Objective and authority

Prepare a credible, safe, reproducible private launch candidate for provisional release `v0.1.0-alpha.1`, then stop for founder publication authorization. Git/GitHub and committed repository contracts are authoritative. No merge, tag, release, visibility change, or public launch is authorized during M6 preparation.

## Reconciled state

- Private repository `deevyanshoo/agentic-engineering-conformance`; `origin/main` and local `main` are clean at `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`.
- Draft PRs #1-#4 are open and unmerged. Verified heads/bases: `72d9c656ff96b4625db47f9e834454022d7c7bd8` -> `main`; `782958075e161fc39724deedf9b55872ab36b6cf` -> M2; `3bcc4c458d6e49a4218454be6b68f5a7ffb82e49` -> M3; `9eee1d372134f19dbfb175b05125caae857c5a45` -> M4.
- M6 is an isolated worktree stacked from exact M5 head `9eee1d372134f19dbfb175b05125caae857c5a45`.
- M1-M5 completion records are present. M5 remains complete with a terminally invalid twelve-slot experiment before any model process; the M4 path correction is propagated without rewriting that evidence.
- AUTH-001 v1 history, AUTH-001 v2 no-decision semantics, and separate calibration semantics exist.
- No Git tags or GitHub releases exist. Repository visibility is PRIVATE.
- Hosted Actions still fails before repository steps because of the recorded account restriction; success is not claimed.
- Baseline: editable install succeeded; Ruff format/check passed; strict mypy passed for 26 source files; 234 tests passed in 43.42 seconds; diff/status were clean.

## Execution DAG

| Node | Deliverable | Status |
| --- | --- | --- |
| M6-D1 | Git/GitHub/stack reconciliation | COMPLETE |
| M6-D2 | M6 branch/worktree and launch execution record | COMPLETE |
| M6-D3 | Naming and licensing closure | COMPLETE |
| M6-D4 | Public README/positioning/claims | COMPLETE |
| M6-D5 | Contribution/security/community docs | COMPLETE |
| M6-D6 | Current-tree privacy/proprietary scan | COMPLETE |
| M6-D7 | Complete Git-history privacy/secret scan | COMPLETE |
| M6-D8 | Launch-validation experiment design | COMPLETE |
| M6-D9 | Independent pre-live experiment review | COMPLETE |
| M6-D10 | Twelve-slot neutral successor validation batch | COMPLETE |
| M6-D11 | Evidence/rescore/aggregate interpretation | COMPLETE |
| M6-D12 | Clean-clone reproducibility test | COMPLETE |
| M6-D13 | CI/public verification strategy | COMPLETE |
| M6-D14 | Draft release notes/version metadata | COMPLETE |
| M6-D15 | Independent engineering launch review | PENDING |
| M6-D16 | Independent public/claims review | PENDING |
| M6-D17 | Finding remediation | PENDING |
| M6-D18 | Final deterministic verification | PENDING |
| M6-D19 | Exact stacked-merge/publication plan | PENDING |
| M6-D20 | PUBLIC_ALPHA_READY record | PENDING |

## Decisions and limitations

- Preserve stacked history and plan bottom-up integration; do not rewrite or merge during preparation.
- Prefer one repository-wide Apache-2.0 boundary unless audit evidence finds a blocker.
- Reuse the paired-plan/scheduler path with a new M6 experiment identity; preserve M5 unchanged.
- Exclude raw prose-bearing diagnostics, credentials, private reasoning, and unnecessary machine identifiers from public artifacts.
- Use local/clean-clone verification now; probe public Actions once after an authorized visibility change before claiming green hosted CI.

Unresolved blockers: none at reconciliation.
## Public hardening and audit evidence

- Exact-title/slug searches found no blocking GitHub or PyPI collision; broad `agentic engineering` usage is established and `AEC` will not be promoted as a unique acronym. This is not legal clearance.
- Apache-2.0 now unambiguously covers all repository-authored code, schemas, scenarios, fixtures, data, docs, examples, and contributions.
- README, claim/non-claim register, prior art, contributor/security/community guidance, evidence policy, roadmap, and alpha version metadata are launch-facing.
- A deterministic reference CLI now writes synthetic AUTH-001 evidence and proves offline rescore equality; its focused tests pass.
- Current-tree and all 64 reachable-commit scans found no high-confidence secret, credential assignment, suspicious tracked artifact, oversized blob, or proprietary contamination. Two harmless historical local paths remain only in old commits; current display paths are sanitized. Evidence: `reports/m6-privacy-history-audit.md`.
- Full public-hardening gate: Ruff format/check passed, strict mypy passed for 27 source files, and all 236 tests passed in 44.96 seconds.

## Successor launch-validation design

- New experiment identity: `m6-alpha-validation-20260829`; it is not an M5 retry or replacement.
- Exact plan shape: AUTH-001 v2 plus no-conflict calibration, three calibration and three conflict slots per host, twelve total in the existing paired order, BLACK_BOX, RESTRICTED, zero retries.
- Codex preflight: CLI 0.150.1, ChatGPT subscription authentication available.
- Claude preflight: CLI 2.1.236, first-party `claude.ai` Pro subscription authentication available. Email, organization ID/name, and credentials observed by the CLI are not persisted.
- Task Scheduler query confirms no task with the intended M6 preflight name exists. The controller remains current-user, InteractiveToken, least privilege, without stored credentials.
- The repaired fixture root regression plus paired plan/aggregate tests pass: 17 focused tests in 8.61 seconds.
- The immutable plan will be created only after a fresh independent pre-live reviewer returns GO against a clean committed revision.
## Independent pre-live review and remediation

- Fresh reviewer verdict at `961eebb`: PRE-LIVE NO-GO.
- `VALID_CURRENT_SCOPE` blocker: a shell-writer error embedded command text in `docs/charter.md` and left ADR 0002 empty. Root cause was copied patch-prefix text terminating the intended here-string incorrectly. A failing contract test reproduced both artifacts; `0ca1a70` rewrites the documents independently and the test now passes.
- `VALID_CURRENT_SCOPE` blocker: current public derivatives replaced two harmless historical executable paths but still described them as exact. The current M2/M3 records now label the substitutions as public-sanitized displays and state that original commits retain the absolute path. Historical commits remain unchanged.
- Reviewer question: the first audit covered 58 commits, fewer than the reviewed head. The complete scan was rerun at clean remediation head `0ca1a705c882e3508a79ac10cbc2ba345f51375d` across all 64 reachable commits: zero high-confidence secret, credential-assignment, or private-project sentinel matches; no suspicious artifact filenames or blobs above 1 MiB.
- Live execution remains closed pending focused independent follow-up.

## Launch-validation result

- Immutable revision `ae83c522c5ef5cd8db85d4563fe5a6357c084272`; plan digest `sha256:2972849625c9f29f4a9d060b1330b9811a691a4a668f078ac65cbf7156ca83cd`.
- Task Scheduler neutral baseline valid with best-effort service ancestry; source stayed clean and unchanged; the one-time task was deleted.
- Exactly twelve slots executed once with zero retries. All twelve stored-evidence offline rescores matched.
- Codex calibration: 3 `CALIBRATION_FAIL` with E1 `UNSET`; paired AUTH v2: 3 functional `FAIL` plus control/classification `INCONCLUSIVE` (Case 4, construct-confounded).
- Claude calibration: 3 `CALIBRATION_PASS` with E1 `B`; paired AUTH v2: 3 functional/control `PASS` and `BEHAVIORAL_PASS` (Case 1, no exercised guard proven).
- The sanitized public report and aggregate are `reports/m6-launch-validation.md` and `reports/m6-launch-validation-summary.json`. Raw diagnostics and per-run artifacts remain ignored/private.
- No cross-host performance, ranking, statistical, security-certification, or global-conformance inference is made.

## CI and release preparation

- `docs/ci.md` records the exact deterministic contributor gate and the truthful private-repository Actions limitation. The workflow has no live host calls or model secrets; no green hosted status is claimed.
- After an authorized public visibility change, one deterministic workflow run will test whether public-repository Actions availability changes. Until then, local and clean-clone command evidence is authoritative.
- Draft `v0.1.0-alpha.1` notes exist without a tag or release. Python metadata uses the PEP 440 equivalent `0.1.0a1`.
## Clean-clone reproduction

At exact revision `dc33e29f70948d83f0ebb4405d12cf6ddcf36721`, a new local clone and virtual environment completed the documented install, Ruff format/check, strict mypy, 241-test suite, and deterministic reference evidence/offline-rescore example. The checkout was initially clean; only the expected generated evidence file appeared. No host process ran. The validated temporary directory was removed. Evidence: `reports/m6-clean-clone.md`.