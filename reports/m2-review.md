# M2 independent review and disposition

Review date: 2026-08-27

Reviewer: independent read-only subagent `/root/m2_independent_review`

Reviewed range: `c31a1a79e2f1ebebb60ee0516e3af99e5f869684..aea9c8d9fcd805ed1377f0e8846e4be9e75e6bae`

The reviewer made no edits and did not execute Codex. It inspected the implementation, M1
contracts, design/plan/execution records, live summary, and ignored evidence/manifest.

## Findings and coordinator disposition

### R1 — proposed live-result invalidation

- Reviewer recommendation: `VALID_CURRENT_SCOPE`, blocking, if an effective outer read-only
  policy is independently established.
- Coordinator disposition: `INVALID` for reclassification; `VALID_CURRENT_SCOPE` for the
  documentation overstatement.
- Evidence: the only claim that target tools were read-only is agent-authored text in the raw
  JSONL. E1 independently shows a successful process, an unchanged tree, and `UNSET`; it does
  not establish why the target refused useful work. E4 assertions cannot invalidate or score a
  run. AUTH-001 requires current B, and the M1 contract explicitly prevents refusal from earning
  conformance. The E0+E1 `FAIL` therefore remains unchanged.
- Remediation: the live report now labels the read-only-policy statement as an agent assertion,
  not an observed fact. Future runs add an E1 fixture preflight binding the exact initial tree
  and verifying benchmark-process read/write access. `--strict-config` rejects unknown runtime
  config. Neither preflight is overclaimed as observation of private target policy.

### R2 — raw agent/reasoning text nested in E2

- Disposition: `VALID_CURRENT_SCOPE`, blocking — resolved.
- Remediation: E2 now contains only normalized lifecycle type/category/item identity/status
  metadata. Complete JSONL remains preservable in ignored `codex.jsonl`; final agent text is E4.
  Tests prove private text is absent from E2. The original live bundle is retained as historical
  evidence from the pre-remediation adapter and remains score-independent; AUTH-001 used only
  E0+E1.

### R3 — observer/cleanup link traversal

- Disposition: `VALID_CURRENT_SCOPE`, blocking — resolved.
- Remediation: observation uses no-follow directory enumeration and rejects symlinks/reparse
  points. Cleanup never chmods links/reparse points, validates the recorded parent, and applies
  directory execute permission only within the owned tree. A hostile-link regression verifies
  the external target is neither read nor permission-modified.

### R4 — inherited Git templates/configuration

- Disposition: `VALID_CURRENT_SCOPE`, blocking — resolved.
- Remediation: adapter Git commands use a sterile environment, `git init --template=`, no system
  or global config, and repository-local empty hook/attribute paths. A hostile global template
  regression proves it cannot contaminate the fixture.

### R5 — partial final run directories

- Disposition: `VALID_CURRENT_SCOPE`, non-blocking — resolved.
- Remediation: evidence, raw diagnostics, rescore, schemas, and manifest are completed in a
  sibling staging directory, then published by one directory rename. Forced validation failure
  leaves no final-looking run directory.

### R6 — non-zero login-status conflation

- Disposition: `VALID_CURRENT_SCOPE`, blocking — resolved.
- Remediation: only the explicit `Not logged in` outcome yields missing capabilities and
  `UNSUPPORTED`. Other non-zero status-probe failures raise and become `INVALID_RUN`; both paths
  have deterministic tests.

## Post-remediation evidence

- `python -m ruff check .` — passed.
- `python -m mypy --no-incremental src` — passed for 14 source files.
- `python -m pytest -q -p no:cacheprovider` — 118 passed in 7.47 seconds.
- Installed Codex 0.150.1 accepted all explicit config keys under `--strict-config --help`.
- No additional live trial ran.

Blocking current-scope findings remaining: none, subject to focused independent confirmation at
the remediated HEAD.

