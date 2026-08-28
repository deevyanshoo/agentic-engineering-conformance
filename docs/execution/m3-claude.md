# M3 Claude Code vertical slice - execution record

Updated: 2026-08-28

Completion state: `IN_PROGRESS`

## Reconciled authority and state

- Private repository: `deevyanshoo/agentic-engineering-conformance`.
- `origin/main`: `c31a1a79e2f1ebebb60ee0516e3af99e5f869684`, unchanged.
- PR #1: draft, open, unmerged; `main` <- `m2/codex-adapter`; head
  `c9474a7b8874472f14a3163d7d30a332066b3cd6`.
- M3 branch: `m3/claude-adapter`, rebased onto that corrected M2 head in an isolated worktree.
- M1 remains `M1_REFERENCE_COMPLETE`; M2 remains historically
  `M2_CODEX_VERTICAL_SLICE_COMPLETE`.
- Corrected M2 gate: Ruff format/check passed, strict mypy passed for 16 source files, 119 pytest
  tests passed, and working-tree/complete branch-range diff checks passed.
- Hosted Actions started zero steps because of the recorded payment/spending-limit restriction.

## Claude authentication gate

- Installed CLI: `2.1.236 (Claude Code)`.
- Local help exposes print mode, JSON/stream-JSON, safe mode, no session persistence, tool
  selection, and permission modes.
- `claude auth status` returned
  `{"loggedIn":false,"authMethod":"none","apiProvider":"firstParty"}`.
- User pause: do not bypass auth, use an API key/Console billing, create or copy credentials,
  fabricate a live result, classify the trial as UNSUPPORTED, or enter the live node.
- Resume only after the exact user signal `CLAUDE_AUTH_COMPLETE`; then independently rerun
  `claude auth status` before any M3 continuation.
- No Claude model call has occurred and no credential or secret was persisted.
- On 2026-08-28, after the user signaled `CLAUDE_AUTH_COMPLETE`, an independent status probe
  returned `loggedIn: true`, `authMethod: claude.ai`, `apiProvider: firstParty`, and
  `subscriptionType: pro`. No key, token, credential file, email, or organization identifier is
  persisted. Authentication transition did not invalidate completed reconciliation.

## Lower-layer observation

The generic AUTH fixture, process seam, and persisted-trial/offline-rescore boundary were corrected
on the owning M2 branch through `c9474a7b8874472f14a3163d7d30a332066b3cd6`, fully verified,
pushed to PR #1, and propagated by rebasing M3. Historical M2 completion remains unchanged; the
later corrections are recorded in the M2 execution history.

## Deterministic implementation evidence

- `ClaudeAdapter` implements the unchanged adapter contract and never calls an oracle or emits a
  benchmark control event.
- Command construction uses documented print/stream-JSON mode, safe mode, no session persistence,
  explicit Sonnet selection, `acceptEdits`, and only repository read/write/search tools.
- JSONL tests cover text-free E2 lifecycle metadata, E4 prose separation, raw preservation,
  forward-compatible unknown events, and malformed/missing terminal output.
- Adapter tests cover probing/authentication, exact invocation, isolated fixture preparation, E1
  final-state capture, timeout/non-zero/missing-state paths, and cleanup containment.
- Cross-host tests prove Codex and Claude share the same adapter interface, AUTH fixture semantics,
  runner/oracle path, and absence of adapter-owned scoring.
- Trial tests prove safe persistence, scenario/fixture binding, and offline rescoring without a host
  invocation.
- Focused gate: Ruff passed; strict mypy passed for 18 source files; 18 Claude/cross-host/trial tests
  passed. The full M3 regression gate remains M3-D10.
- M3-D10 full local gate: Ruff format/check passed; strict mypy passed for 18 source files; all
  137 tests passed; branch-range and working-tree `git diff --check` passed. The initial format
  check identified two CRLF-normalization-only test files; the configured formatter corrected them
  before the successful full rerun.

## Execution DAG

| Node | Deliverable | Status |
| --- | --- | --- |
| M3-D1 | Repository/PR/worktree reconciliation | COMPLETE |
| M3-D2 | Claude CLI/auth surface reconciliation | COMPLETE |
| M3-D3 | Stacked branch/worktree and durable record | COMPLETE |
| M3-D4 | Generic fixture/lower-layer correction | COMPLETE |
| M3-D5-D9 | Claude adapter and cross-host deterministic tests | COMPLETE |
| M3-D10 | Full local regression gate | COMPLETE |
| M3-D11 | Exactly one live Claude AUTH-001 trial | PENDING |
| M3-D12 | Stored-evidence rescore | PENDING |
| M3-D13-D14 | Independent review and remediation | PENDING |
| M3-D15 | Final local deterministic verification | PENDING |
| M3-D16 | Push stacked branch and draft PR | PENDING |
| M3-D17 | Completion record | PENDING |

No Claude model call has occurred. M3 resumes at the full local regression gate, M3-D10; live,
review, and completion nodes remain pending.
