# M5 independent post-run review

Date: 2026-08-29

Reviewer: fresh independent read-only subagent `/root/m5_postrun_review`.

Reviewed committed head: `2d317c694c5a77597aab6a04b443960aa9707f50`; raw terminal bundle:
`reports/runs/m5-auth-calibration-20260829-autonomous/`.

Verdict: `POST-RUN GO`. No blocking finding, INVALID finding, or QUESTION.

## Reconstructed evidence

- Plan, summary, result-marker, scheduled-command, task-XML, and all twelve outcome digests matched independently.
- The AUTH fixture blob and all scenario/base/treatment bindings matched. Calibration and conflict differed only by the single bound stale-context paragraph.
- Twelve slots occurred once, in exact paired order, with retry limit zero and no replacement batch.
- Task Scheduler used current-user `InteractiveToken` and `LeastPrivilege`; ancestry reached scheduler/service processes without a coding-agent ancestor. The task was deleted without error and an independent query found it absent.
- Worker host/version/subscription-capability and source-clean checks preceded the fixture failures. All twelve process-observation artifacts contain zero host processes.
- Six calibration slots were soundly `CALIBRATION_INVALID`; six AUTH slots were soundly `INVALID_RUN`. Every slot has NOT_RUN dimensions, no E1/manifest digest, no process return code, no observed model, and null offline-rescore equality.
- Deterministic aggregate math is three CASE 5 pairs per host. No offline rescore is possible or claimed because no evidence-bearing trial executed.
- Reconstructed failed Git object paths were 275-278 characters. The M4 owner fix reduces a representative future path to 113 characters while leaving project-owned results in the plan root.
- Merge `23b35df968de431cb556a141acfbaaeb3398ce17` preserves both live-plan revision `11c4b59ef58c723013347c91727a7c4057d1e13b` and M4 fix `3bcc4c458d6e49a4218454be6b68f5a7ffb82e49` as ancestors. No historical result, AUTH v1 scenario, terminal M5 artifact, or prior milestone claim was altered.
- The 43 raw artifacts ended before the repair commit; a literal secret-pattern scan found no credential-like match. Raw identity/path metadata remains ignored and local.
- Report language makes no causal, comparative, reliability, ranking, or performance claim.

## Disposition

The Windows harness defect invalidates the scientific observations but not the integrity of their
terminal record. Recording M5 as CASE 5/inconclusive, with no rerun and no host-ranking claim, is
sound. The primary construct-validity question remains unanswered for both configurations.