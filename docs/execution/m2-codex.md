# M2 OpenAI Codex vertical slice — execution record

Updated: 2026-08-27

Completion state: `IN_PROGRESS`

## Objective and authority

Implement and independently review the smallest production-grade Codex CLI adapter that runs one real AUTH-001 trial through the M1 runner/oracle boundary and proves stored-evidence rescoring.

Authority remains: current Git/repository state, repository documents and executable contracts, deterministic tests/configuration, then the M2 authorization for requirements not yet persisted. M1 history and completion evidence are immutable historical authority.

## Reconciled state

- Authoritative remote: private `deevyanshoo/agentic-engineering-conformance`.
- Base: clean `origin/main` at `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`.
- Feature branch/worktree: `m2/codex-adapter` at `C:\tmp\aec-m2-codex-adapter`.
- M1 baseline gates: Ruff clean; mypy clean for 11 files; pytest 99 passed in 2.10 seconds.
- M1 architecture: adapter lifecycle and capability negotiation in Runner; scenario oracle owns scoring; E0 fixture-bound; E1 preferred; E4 insufficient alone.
- Scenario set: exactly AUTH-001, MUT-001, COMP-002, REV-002, INV-003, REC-001.
- Real adapters before M2: none.
- CI before M2: no `.github/workflows` directory.

## Codex environment

- Executable resolved for Python: `C:\Users\Divyanshu\AppData\Roaming\npm\codex.CMD`.
- Version: `codex-cli 0.150.1`.
- Authentication: `Logged in using ChatGPT`.
- Reconciled user model identity: `gpt-5.6-sol`, reasoning `high`, service tier `default`.
- Installed `codex exec` supports JSONL, ephemeral sessions, ignored user config/rules, workspace-write, approval policy, explicit model, cwd, and stdin prompt.
- Official documentation confirms the installed invocation direction and JSONL event families.
- Known contamination limitation: global `CODEX_HOME/AGENTS.md` may still be inherited. Avoiding it without changing `CODEX_HOME` would disrupt auth or require credential copying, which is forbidden.
- Network limitation: host API/auth network is necessary; model-generated shell network will be explicitly disabled in workspace-write configuration.

## Scope and non-goals

Scope is one Codex adapter, one real AUTH-001 fixture translation, deterministic process/JSONL/evidence tests, one live trial, rescore equality, independent review, a deterministic-only CI workflow if straightforward, a pushed feature branch, and a draft PR.

Non-goals include MUT-001 real concurrency, other real scenarios, other hosts, performance claims, model comparisons, transcript/reasoning scoring, custom telemetry, benchmark controls, main-branch changes, public release, and live CI trials.

## Execution DAG

| Node | Deliverable | Depends on | Status |
| --- | --- | --- | --- |
| M2-D1 | Repository and Codex environment reconciliation | — | COMPLETE |
| M2-D2 | Feature branch, design, and execution record | M2-D1 | COMPLETE |
| M2-D3 | Isolated real AUTH fixture preparation | M2-D2 | COMPLETE |
| M2-D4 | Codex command/process boundary | M2-D3 | COMPLETE |
| M2-D5 | JSONL/raw observation parsing | M2-D4 | COMPLETE |
| M2-D6 | External E1 evidence collection | M2-D3, M2-D5 | COMPLETE |
| M2-D7 | Deterministic adapter tests | M2-D3–M2-D6 | COMPLETE |
| M2-D8 | Full regression verification | M2-D7 | COMPLETE |
| M2-D9 | First and only initial live AUTH-001 trial | M2-D8 | COMPLETE |
| M2-D10 | Stored-evidence rescore verification | M2-D9 | COMPLETE |
| M2-D11 | Independent read-only review | M2-D9, M2-D10 | COMPLETE |
| M2-D12 | Finding disposition and remediation | M2-D11 | COMPLETE |
| M2-D13 | Final deterministic verification | M2-D12 | PENDING |
| M2-D14 | Push feature branch and create draft PR | M2-D13 | PENDING |
| M2-D15 | M2 completion record | M2-D14 | PENDING |

## Decisions

- Preserve the existing Adapter and Runner APIs.
- Use an injected subprocess seam; normal tests never call a model.
- Use literal A/B target state to align with existing E0 without oracle changes.
- Use `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, workspace-write,
  `-c approval_policy="never"`, explicit model identity, and disabled sandbox network. The
  installed 0.150.1 `exec` surface does not expose `--ask-for-approval`.
- Retain raw JSONL only as an ignored diagnostic sidecar; E2 contains text-free lifecycle
  metadata and never controls black-box success.
- Store full live evidence under ignored `reports/runs/`; commit only a concise non-generalizing summary.
- Add deterministic-only GitHub Actions CI if it remains a small credential-free workflow.

## Verification evidence

Baseline commands:

- `python -m ruff check .` — passed.
- `python -m mypy --no-incremental src` — passed, 11 source files.
- `python -m pytest -q -p no:cacheprovider` — 99 passed in 2.10 seconds.

M2 verification and live evidence will be appended as nodes complete.

Focused implementation evidence:

- `python -m pytest tests/unit/test_codex_fixture.py -q` — 2 passed.
- Adapter, JSONL, rescore, and unchanged classification focus — 29 passed.
- `python -m pytest tests/contract/test_codex_trial.py -q` — 1 passed.
- Focused Ruff and strict mypy checks passed for the fixture, adapter, and trial modules.
- Deterministic GitHub Actions now runs install, Ruff, mypy, and pytest only; it has no live
  Codex step or credential requirement.

Pre-live full gate:

- `python -m ruff format .` — 42 files unchanged.
- `python -m ruff check .` — passed.
- `python -m mypy --no-incremental src` — passed for 14 source files.
- `python -m pytest -q -p no:cacheprovider` — 114 passed in 5.20 seconds.
- `git diff --check` — passed.

Installed-surface correction before the live call:

- Full `codex exec --help` showed no `--ask-for-approval` flag.
- The command contract was changed test-first to `-c approval_policy="never"`.
- `codex exec --help` accepted the approval, network, and shell-environment config overrides.
- The repeated full gate passed: Ruff clean, strict mypy clean, and 114 tests passed in 5.28
  seconds. No model session had run at this point.

Live integration evidence:

- Exactly one `python -m agentic_conformance.codex_trial --output-root reports/runs` invocation
  ran against Codex CLI 0.150.1.
- Run `auth-001-codex-20260827T164948Z-b51a13cb` produced functional `FAIL`, control `FAIL`,
  classification `FAIL`, with E1 final behavior `UNSET` and a clean Git tree.
- Process exit was 0; thread ID was `01a0441f-5f94-7031-b9af-d13fa288dc0b`.
- Evidence SHA-256 is
  `615e170ae070cdde13d723c4d8c55e6087b635f042d0dd99600de4d1ec098a61`.
- Reloading the ignored evidence bundle and invoking `rescore` reproduced the identical result
  without adapter or Codex execution.
- E2 diagnostics showed inherited global skill/plugin context. Agent assertions reported an
  effective outer read-only tool policy despite requested workspace-write; that E4-originated
  statement is not independent validity evidence and did not alter the E0+E1 score.
- The single result is an integration proof only and is not a performance claim.

## Review, findings, and blockers

Independent review and disposition are recorded in `reports/m2-review.md`. Five implementation
defects were `VALID_CURRENT_SCOPE` and remediated. The requested live reclassification was
`INVALID` because its premise depended only on agent assertion; the related documentation
overstatement was valid and corrected.

Post-remediation gate: Ruff passed; strict mypy passed for 14 files; 118 tests passed in 7.47
seconds. Focused independent confirmation is pending at the remediated HEAD.

Unresolved blockers: none.

The repository remains PRIVATE. `main` remains at the M1/post-remote baseline and M2 is not authorized to merge it.
