# M4 neutral autonomous experiments - execution record

Updated: 2026-08-28

Completion state: `IN_PROGRESS`

## Objective and authority

M4 validates repeatable, autonomous AUTH-001 execution through a neutral operating-system
scheduler boundary. It plans exactly three OpenAI Codex and three Claude Code trials, scores each
from E0 plus E1 in BLACK_BOX mode, verifies offline rescore equality, and emits a deterministic
non-ranking aggregate. This milestone does not compare host performance.

The current repository, Git/GitHub state, M1-M3 execution records, and committed benchmark
contracts are authoritative. Founder authorization dated 2026-08-28 supersedes the earlier
human-launch requirement for M4-D14. It authorizes one temporary current-user Windows scheduled
task and existing subscription authentication; it does not authorize API keys, credential
copying, administrator elevation, public release, merging, or live trials in GitHub Actions.

## Reconciled state

- Private repository: `deevyanshoo/agentic-engineering-conformance`; default branch `main`.
- `origin/main`: `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`, unchanged.
- PR #1 is draft/open/unmerged with M2 head
  `ccae3930d2e758bc26676eeeccae36290eda3ab2`.
- PR #2 is draft/open/unmerged with M3 head
  `14b48c5679c93eda5c7b004dfe3494ffb0556494`.
- M4 branch `m4/neutral-experiments` was created from that exact M3 head in an isolated worktree.
- M1, M2, and M3 completion records remain historical truth; their live trials are not replaced
  or reclassified by M4.
- Baseline local gate at M3 head: Ruff format/check passed, strict mypy passed for 18 source
  files, all 143 tests passed, and the M4 worktree was clean.
- GitHub-hosted deterministic CI remains externally unavailable before workflow steps; success is
  not claimed and M4 will use repository-owned local gates.

## Host and scheduler preflight

- Codex executable present; version `codex-cli 0.150.1`; subscription authentication reported
  `Logged in using ChatGPT` without a model call.
- Claude Code executable present; version `2.1.236`; sanitized authentication status reported
  logged in via `claude.ai`, first-party provider, Pro subscription.
- Current Windows identity: `desktop-pm3kt77\\divyanshu`.
- Windows 10.0.19045 with Windows PowerShell 5.1; Task Scheduler command and PowerShell surfaces
  are installed.
- No M4 scheduled task has been registered and no M4 model call has occurred.

Authentication/capability preflight will be repeated by the neutral worker before any model call.
No token, credential file, account email, organization identifier, cookie, or complete environment
dump is persisted.

## Decisions and validity boundary

- The worker will be launched once by Windows Task Scheduler under the current interactive user,
  with least privilege, no stored password, no highest-privilege setting, and no shell command
  interpolation.
- An immutable JSON plan will bind exact benchmark revision, scenario and fixture identities,
  adapter/CLI identities, requested profiles, six fixed run IDs and alternating order, policies,
  output root, retry limit, and its canonical digest.
- Worker and host process ancestry will be recorded best-effort using an allowlisted envelope.
  Direct ancestry beneath a known coding-agent process, or absence of scheduler evidence, makes
  the batch `INVALID_NEUTRAL_ENVIRONMENT` before live execution.
- The worker rejects revision/binding mismatch or an unexpectedly dirty source tree and never
  edits benchmark source. The outer implementation process performs no source mutation while the
  task runs.
- Each executed run is persisted atomically through existing trial persistence and immediately
  reloaded/rescored. Optional lifecycle evidence remains text-free E2; agent prose is E4 or an
  ignored raw diagnostic.
- Trial order is Codex 1, Claude 1, Codex 2, Claude 2, Codex 3, Claude 3. Retry count is zero; an
  invalid trial is retained and never cosmetically replaced.
- M4 records `NEUTRAL_AUTONOMOUS_BASELINE`, actual limits, and observations only. N=3 per host
  supports no winner, ranking, pass-rate inference, or statistical superiority claim.

## Findings, verification, and blockers

- No current blocker.
- Pre-live and post-run independent review evidence will be added without rewriting earlier
  history.
- Scheduled-task registration, execution, cleanup, trial evidence, aggregate digests, and final
  verification remain pending.

## Execution DAG

| Node | Deliverable | Status |
| --- | --- | --- |
| M4-D1 | Repository/PR/worktree reconciliation | COMPLETE |
| M4-D2 | Stacked branch/worktree and durable execution record | IN_PROGRESS |
| M4-D3 | Neutral operator/worker architecture | PENDING |
| M4-D4 | Sanitized environment envelope | PENDING |
| M4-D5 | Process-ancestry validity detection | PENDING |
| M4-D6 | Immutable experiment-plan contract | PENDING |
| M4-D7 | Autonomous worker | PENDING |
| M4-D8 | Task Scheduler launcher/controller | PENDING |
| M4-D9 | Deterministic aggregate reader | PENDING |
| M4-D10 | Deterministic M1-M4 regression tests | PENDING |
| M4-D11 | Independent pre-live review | PENDING |
| M4-D12 | Pre-live remediation | PENDING |
| M4-D13 | Final deterministic pre-live verification and clean commit | PENDING |
| M4-D14 | Register one-time neutral scheduled task | PENDING |
| M4-D15 | Autonomous six-trial batch | PENDING |
| M4-D16 | Per-run offline rescore verification | PENDING |
| M4-D17 | Aggregate generation | PENDING |
| M4-D18 | Scheduled-task cleanup | PENDING |
| M4-D19 | Independent post-run review | PENDING |
| M4-D20 | Post-run remediation | PENDING |
| M4-D21 | Final deterministic verification | PENDING |
| M4-D22 | Push stacked branch and create draft PR | PENDING |
| M4-D23 | Completion record | PENDING |
