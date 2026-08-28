# M3 independent review

Date: 2026-08-28

Reviewer: `/root/m3_independent_review`, independent read-only subagent.

Reviewed range:
`c9474a7b8874472f14a3163d7d30a332066b3cd6..f100f1e6777e53b94e93cdedce0a2bd051412779`.

The reviewer changed no file, Git state, GitHub state, credential state, or host state and did not
invoke Claude. The exact historical review range precedes the lower-layer correction/rebase; its
findings were remediated on the owning branches described below.

## Review strengths

- The generic Runner/oracle path had no Claude-specific branch.
- The command surface was narrow and non-intervening.
- E1 scoring, text-free optional E2, E4 prose, and raw sidecar roles were separated.
- The persisted live bundle and all three reported SHA-256 digests matched.
- The recorded live terminal event and E1 behavior supported the unchanged
  `BEHAVIORAL_PASS` result.
- The N=1 non-claim and managed-policy limitation were explicit.

## Finding dispositions

### R1 - logged-out exit status

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved.
- Evidence: the official CLI contract uses exit 1 for logged out, but the probe rejected every
  nonzero status before parsing JSON.
- Remediation: status 0 or 1 now enters schema validation; `loggedIn:false` yields empty
  capabilities/UNSUPPORTED, while genuine probe errors and inconsistent logged-in exit status
  remain INVALID_RUN. See `adapters/claude.py:271-287` and
  `tests/unit/test_claude_adapter.py:87`.

### R2 - failed terminal event accepted

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved.
- Evidence: any `type=result` event was accepted regardless of error subtype/flag.
- Remediation: only a success subtype without an error flag is terminally admissible; empty,
  unterminated, malformed, and explicit error streams invalidate the run. See
  `adapters/claude.py:174-194` and `tests/unit/test_claude_jsonl.py:112-130`.

### R3 - stale real-host fixture translation

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved on owning M2 layer.
- Evidence: both real-host translations checked only the scenario ID while hard-coding A/B
  fixture semantics.
- Remediation: shared validation binds version, canonical definition digest, and canonical
  fixture ground truth. Codex and Claude call it before preparation. M2 commit `ccae393` was
  verified with 121 tests, pushed to PR #1, and propagated into M3. See
  `adapters/auth_fixture.py:61`, `adapters/codex.py:189`, and `adapters/claude.py:291`.

### R4 - exact invocation absent from committed report

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved.
- Remediation: `reports/m3-claude-live.md` now records the literal ordered argv captured by E1.

### R5 - truncated limitation documents

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved.
- Remediation: the architecture restores the M1/M2 non-claims and adds the N=1 M3 boundary; the
  live report completes its no-ranking sentence.

### R6 - deterministic coverage overstatement

- Disposition: `VALID_CURRENT_SCOPE`, blocking, resolved.
- Remediation: deterministic regressions now cover empty, unterminated, and error terminal output,
  official logged-out exit 1, and changed same-ID scenario rejection before host execution.

## Reviewer questions

- Fixture-root replacement: `QUESTION`, non-blocking. Coordinator disposition: outside the
  current target tool/threat surface; a hostile operating system is an explicit non-claim.
  Inner-tree symlink/reparse containment remains covered.
- Administrator-managed Claude policy: `QUESTION`, non-blocking. Coordinator disposition:
  accepted explicit contamination limitation. It is not credited as an adapter or benchmark
  control and does not alter the black-box E0+E1 live score.

## Remediation evidence

- TDD red: three intended failures reproduced logged-out, failed-terminal, and stale-binding bugs.
- Focused green: 33 shared/Claude adapter and parser tests passed.
- Post-remediation suite: 143 tests passed; strict mypy passed for 18 source files; Ruff lint
  passed. The final complete deterministic gate and independent confirmation follow on the
  committed remediation head.

No live rerun occurred. No result was changed to improve the recorded Claude outcome.
