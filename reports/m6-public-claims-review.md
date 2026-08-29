# M6 independent public and claims launch review

Date: 2026-08-29

Reviewer: fresh independent read-only subagent. Reviewed clean head `3cac5d8f1209adeecf62bed267ea81c636e3a165` against M5 base `9eee1d372134f19dbfb175b05125caae857c5a45` without mutation or model calls.

Initial verdict: **PUBLIC/CLAIMS LAUNCH NO-GO**.

## Findings and disposition

- Critical `VALID_CURRENT_SCOPE`, blocking: two current M4 derivatives contained an unnecessary combined machine/user identity and the earlier audit omitted it. Accepted. Commit `8872400` replaces current displays with role descriptions, labels them as public-sanitized derivatives, preserves historical commits, adds machine-principal regression coverage, and reruns the full audit.
- High `VALID_CURRENT_SCOPE`, blocking: architecture still said AUTH v2/calibration awaited a successor. Accepted. Commit `8872400` records the distinct completed M6 successor and its limited exact-run interpretations.
- Medium `VALID_CURRENT_SCOPE`, blocking: draft release wording could read as an unsupported field-priority claim. Accepted. Commit `8872400` scopes it to this project's initial vertical slice.
- Low `VALID_CURRENT_SCOPE`, nonblocking: clean-clone evidence said exact quickstart although it used equivalent/stricter documented gates. Accepted and corrected.
- Low `VALID_OUT_OF_SCOPE`, nonblocking: harmless old local executable paths remain in history. Historical provenance remains intact and current derivatives stay sanitized.

The reviewer otherwise found the README, claim register, M5/M6 distinction, AUTH/calibration wording, prior art, naming assessment, licensing, contributor/security documents, CI disclosure, links, artifact exclusions, and aggregate narrative credible and appropriately limited. A focused read-only follow-up is required to close the three remediated blockers.