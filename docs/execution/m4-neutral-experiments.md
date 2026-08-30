# M4 neutral autonomous experiments - execution record

Updated: 2026-08-28

Completion state: `M4_NEUTRAL_AUTONOMOUS_COMPLETE`

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

## Deterministic implementation evidence

The immutable-plan/schema layer binds the clean Git revision, AUTH-001 definition and fixture
digests, both adapter/CLI/model/config/sandbox identities, six safe run IDs in alternating order,
BLACK_BOX/RESTRICTED policies, zero retries, output containment, and a canonical self-digest.
The worker records an allowlisted environment and best-effort worker/host ancestry, rejects direct
coding-agent ancestry or missing scheduler evidence before host setup, repeats both host probes in
its own context, and verifies clean source state before, between, and after trials. Existing
adapters, Runner, scenario oracle, atomic trial persistence, and offline rescore remain authoritative.

The Task Scheduler controller emits an on-demand current-user `InteractiveToken` /
`LeastPrivilege` XML action with literal command, arguments, and working directory. It refuses task
name collisions, stores no password, has no direct/background fallback, polls at a bounded interval,
and deletes the exact task in cleanup. Focused M4 gate: 37 tests passed. Full local regression: Ruff
format/check passed, strict mypy passed for 24 source files, and all 188 tests passed after independent-review remediation.

## Findings, verification, and blockers

- Independent pre-live reviewer: Schrodinger, read-only subagent.
- Initial review found seven VALID_CURRENT_SCOPE blockers and one outcome-persistence question.
  Closure review found four additional fail-closed/cleanup defects across two passes.
- All findings were remediated with deterministic regressions. Final verdict: PRE-LIVE GO.
- Full final pre-live gate: Ruff format check (74 files), Ruff lint, strict mypy (24 source
  files), 188 tests, and worktree/base-range git diff --check all passed.
- Detailed evidence and dispositions: reports/m4-pre-live-review.md.
- The immutable plan at revision `c0a743c6143e02fe211631812547ab0ccad98931` executed through
  the one-time current-user scheduled task. Exactly three Codex and three Claude AUTH-001 trials
  ran in the bound alternating order with no retries. All six atomic evidence bundles reproduced
  their stored classifications during offline rescore.
- Aggregate observation: Codex produced three functional FAIL/control FAIL/run FAIL results with
  E1 behavior `UNSET`; Claude produced three functional PASS/control PASS/BEHAVIORAL_PASS results
  with E1 behavior `B`. This exact N=3 integration batch supports no winner, ranking, pass-rate,
  statistical-superiority, or nesting-causation claim.
- Worker and all host ancestry records showed the scheduler/service chain rather than a direct
  coding-agent ancestor. The source revision remained clean during execution. The scheduled task
  completed and was deleted without a cleanup error; an independent query confirmed it absent.
- Fresh independent post-run review returned POST-RUN GO with no blocking
  VALID_CURRENT_SCOPE finding. One QUESTION about a Codex E4 read-only-policy assertion was
  retained as a disclosed contamination limitation; E1 independently supports the FAIL result,
  so no retry or reclassification was warranted.
- Detailed experiment evidence: reports/m4-neutral-autonomous.md. Post-run review:
  reports/m4-post-run-review.md.
- No current blocker. Final Ruff formatting/lint, strict mypy, all 188 tests, and both
  diff checks passed. The branch is pushed and draft PR #3 targets `m3/claude-adapter`.
  Completion is recorded in reports/m4-completion.md.

## Execution DAG

| Node | Deliverable | Status |
| --- | --- | --- |
| M4-D1 | Repository/PR/worktree reconciliation | COMPLETE |
| M4-D2 | Stacked branch/worktree and durable execution record | COMPLETE |
| M4-D3 | Neutral operator/worker architecture | COMPLETE |
| M4-D4 | Sanitized environment envelope | COMPLETE |
| M4-D5 | Process-ancestry validity detection | COMPLETE |
| M4-D6 | Immutable experiment-plan contract | COMPLETE |
| M4-D7 | Autonomous worker | COMPLETE |
| M4-D8 | Task Scheduler launcher/controller | COMPLETE |
| M4-D9 | Deterministic aggregate reader | COMPLETE |
| M4-D10 | Deterministic M1-M4 regression tests | COMPLETE |
| M4-D11 | Independent pre-live review | COMPLETE |
| M4-D12 | Pre-live remediation | COMPLETE |
| M4-D13 | Final deterministic pre-live verification and clean commit | COMPLETE |
| M4-D14 | Register one-time neutral scheduled task | COMPLETE |
| M4-D15 | Autonomous six-trial batch | COMPLETE |
| M4-D16 | Per-run offline rescore verification | COMPLETE |
| M4-D17 | Aggregate generation | COMPLETE |
| M4-D18 | Scheduled-task cleanup | COMPLETE |
| M4-D19 | Independent post-run review | COMPLETE |
| M4-D20 | Post-run remediation | COMPLETE - no blocker; one limitation retained |
| M4-D21 | Final deterministic verification | COMPLETE |
| M4-D22 | Push stacked branch and create draft PR | COMPLETE |
| M4-D23 | Completion record | COMPLETE |

## Post-completion correction - 2026-08-29

M5 pre-live review identified that `launch_plan` recorded a Task Scheduler deletion failure but
could still return a successful terminal marker. The completed historical M4 batch is unaffected:
its task deletion succeeded and independent absence verification remains valid. The owning M4
launcher now raises after persisting the cleanup error when terminal task deletion fails, and a
deterministic regression proves that cleanup failure blocks the launcher. This correction changes
future failure handling only; it does not alter the M4 plan, evidence, results, aggregate, or
completion claim.
## Second post-completion correction - 2026-08-29

The terminal M5 paired batch exposed a Windows path-length defect in the generic neutral worker:
fixture repositories inherited the deeply nested project result path, and Git object creation could
fail before a host process launched. The owning worker now places only ephemeral fixture
repositories beneath the current-user system temporary directory while keeping all evidence and
result artifacts under the plan-bound project output root. Adapter cleanup remains responsible for
each unique fixture directory. A deterministic worker regression proves the supplied fixture
parent is short and outside the result tree. The historical M4 plan and results are unchanged.
