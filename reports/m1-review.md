# M1 independent review

Date: 2026-08-27

Reviewer: independent read-only Codex subagent `/root/m1_independent_review` (not the implementation writer).

Reviewed range: `6beb272..9012861effdc1a276b5ad1b37918dd1879dcda9a`. The reviewer confirmed HEAD and a clean working tree, then independently ran `python -m pytest -q`: 46 passed in 0.77 seconds.

## Finding dispositions

| ID | Severity | Disposition | Finding | Required remediation |
| --- | --- | --- | --- | --- |
| R1 | CRITICAL | VALID_CURRENT_SCOPE | Adapter-supplied ground truth can redefine benchmark E0. | Fixture-verify in benchmark-owned loading; normalize collected bundles to scenario E0; reject E0 mismatch on rescore. |
| R2 | HIGH | VALID_CURRENT_SCOPE | Artifact digest covers payload only, so provenance metadata can be relabeled. | Digest the complete evidence envelope and test every protected field. |
| R3 | HIGH | VALID_CURRENT_SCOPE | Functional INCONCLUSIVE masks control FAIL. | Give control FAIL classification precedence and test the matrix. |
| R4 | HIGH | VALID_CURRENT_SCOPE | GUARDED_PASS trusts unbound exercise/control labels. | Enforce scenario exercise semantics, required evidence, provenance levels, uniqueness, and subject/run binding. |
| R5 | HIGH | VALID_CURRENT_SCOPE | Completion/review ignore artifact subject metadata; review independence is ignored. | Score artifact envelopes and require consistent current subject plus independent review. |
| R6 | HIGH | VALID_CURRENT_SCOPE | Reconstruction expectation is derived from adapter-observed durable state and is circular. | Use fixture-bound E0 ground truth, independently check durable state, and test consistently fabricated state. |
| R7 | MEDIUM | VALID_CURRENT_SCOPE | Stored bundle parser ignores schema version and extra/missing fields. | Add strict versioned closed parsing and compatibility tests. |
| R8 | MEDIUM | VALID_CURRENT_SCOPE | Invalid `probe()` values escape INVALID_RUN handling. | Validate/normalize capabilities within the lifecycle exception boundary. |
| R9 | MEDIUM | VALID_CURRENT_SCOPE | Result schemas/models accept impossible semantic combinations. | Add model invariants and JSON Schema conditionals with malformed-combination tests. |

No finding is deferred as out of scope. All nine affect M1 experimental validity or an explicit completion condition and must be resolved before D14.

## Remediation evidence

Implementation coordinator status: all nine findings remediated; final independent confirmation pending.

- **R1:** benchmark loader now verifies and owns fixture E0; runner normalizes collected artifacts onto scenario E0; rescore rejects ground-truth mismatch. Regressions: adapter substitution and stored E0 substitution.
- **R2:** artifact digest now covers ID, level, kind, producer, payload, and subject. Regressions mutate each envelope field independently, and the public value constructor validates canonical data plus the complete envelope digest.
- **R3:** control FAIL precedes functional INCONCLUSIVE. Regression covers PASS/FAIL/INCONCLUSIVE functional values.
- **R4:** scenarios now declare kind/level/producer/cardinality evidence contracts and exact exercise conditions; guarded response requires a scenario-bound exercise plus a linked E2 host event. Required kinds reject shadow artifacts with undeclared levels or producers. Regressions cover label-only, wrong-level, wrong-producer, duplicate, unbound, and shadow evidence.
- **R5:** completion/review score artifact envelopes against E0 current candidate, and current satisfied review requires `independent: true`. Regressions cover wrong artifact subjects and non-independent current approval.
- **R6:** REC-001 compares observed durable state and reconstruction with fixture-owned E0; its interpreter is separately checked against hand-authored expected reconstruction. Regression covers consistently fabricated matching artifacts.
- **R7:** v0.1 stored bundle/artifact parsing is closed, versioned, and digest-validating. Regressions cover future version, extra fields, missing fields, and artifact extras.
- **R8:** probe normalization/type validation is inside the lifecycle error boundary. Regression confirms invalid probe output yields INVALID_RUN.
- **R9:** typed results and both persisted schemas enforce classification/outcome/response semantics in both directions. Executed classifications reject `NOT_RUN` in either dimension. Regressions cover impossible terminal, guarded, fail, and inconclusive combinations.

Fresh coordinator verification after remediation: Ruff passed; strict mypy passed for 11 source files; pytest reported 72 passed in 1.08 seconds.

## Focused follow-up review

The same independent reviewer checked remediation commit `ad3b36745c7837dc3e39720ca455bd6e05901c9e`, confirmed a clean tree, and independently ran Ruff, mypy, and pytest (72 passed in 1.04 seconds). It confirmed R1, R3, R5, R6, R7, and R8 resolved, but found the first remediation incomplete for:

- **R2:** direct `EvidenceArtifact(...)` construction could still supply a forged digest.
- **R4:** a valid required artifact could be shadowed by a later same-kind artifact with the wrong level or producer.
- **R9:** FAIL and INCONCLUSIVE could still contain a `NOT_RUN` dimension in the model and schemas.

The coordinator accepted all three as continued `VALID_CURRENT_SCOPE` findings and reproduced them with failing tests before changing implementation. The second remediation added constructor-level envelope validation, conservative rejection of same-kind out-of-contract evidence, and a shared executed-classification `NOT_RUN` invariant in the model and both schemas. Fresh coordinator gates after the second remediation: Ruff passed; strict mypy passed for 11 source files; pytest reported 99 passed in 1.66 seconds.

## Positive evidence

The reviewer found disciplined scope, exactly six scenarios, separate functional/control fields and cross-product tests, correct normal UNSUPPORTED short-circuiting, normal adapter exception handling and cleanup, immutable payload snapshots, scenario identity binding during rescoring, fixture/scenario count checks, and conservative documentation/claims.

## Completion assessment

At reviewed HEAD `9012861`, `M1_REFERENCE_COMPLETE` was not supportable. Both remediation rounds are implemented, but completion remains pending the reviewer's final confirmation and D14 verification.
