# M6 repository privacy, secret, and contamination audit

Date: 2026-08-29

Exact audited remediation head: `8872400b9a771bafb54ef4a76a10fc226dcf1bd8`

Scope: all 147 tracked launch-candidate files at the audited head and all 70 commits then reachable from local/remote refs across `main` and the M2-M6 stack. Values matching sensitive patterns were never printed; scans reported counts or paths for classification only. A final exact-head read-only scan remains part of M6-D18 after the completion record is committed.

## Current-tree results

- Boundary-aware high-confidence token/key/private-key shapes: no matches. An initial broad token detector matched a standards URL substring; token-boundary correction classified it as a false positive and returned zero.
- Credential assignments (`api_key`, OAuth/access token, client secret, password, cookie): no matches.
- Founder-supplied private-project sentinel: no matches.
- Absolute user-home paths: no matches.
- Combined machine/user principals: no matches after the public/claims review identified and the current M4 derivatives sanitized two unnecessary displays.
- Email-shaped content appears in two paths: the synthetic `fixture@example.invalid` identity and this audit's description of that synthetic fixture.
- Tracked `.env`, key/certificate, JSONL, log, database, archive, executable, or binary artifacts: none.
- Tracked files larger than 1 MiB: none.
- Raw host transcripts or prose-bearing diagnostic sidecars: none tracked. Source/tests mention their exclusion or classification but contain no transcript.
- Ignored cache/build directories are local only; `reports/runs/` and its live artifacts remain ignored and untracked.

## Reachable-history results

- Boundary-aware high-confidence token/key/private-key shapes: zero matching commits.
- Credential assignments: zero matching commits.
- Founder-supplied private-project sentinel: zero matching commits.
- Suspicious credential/log/transcript/binary filenames: none reachable.
- Blobs larger than 1 MiB: none reachable.
- Email-shaped file content is synthetic fixture/audit material. One configured Git author identity exists in commit metadata and is treated as intentional public authorship; the email is not duplicated here.
- Older M2/M3 commits retain two harmless local executable paths. Current public derivatives use `%APPDATA%` and explicitly disclose their sanitized status.
- Older M4 commits retain a harmless local machine/user principal in historical scheduler records. Current public derivatives replace it with a role description and explicitly disclose that the original commit retains local context.
- These historical strings contain no credential or secret. Destructive stack-wide rewriting would add disproportionate provenance risk, so the history is preserved and the current public tree is sanitized.

## Proprietary contamination gate

The sentinel and focused domain scans found no private repository name, customer information, proprietary architecture, financial-product methodology, regulatory reasoning, private roadmap, copied proprietary implementation, or private research. All fixtures are small synthetic engineering states.

Result: **NO PROPRIETARY CONTAMINATION FOUND.**

## Commands and disposition

The audit used boundary-aware regular expressions over `git ls-files`, `git grep -l` across every `git rev-list --all` commit, filename history from `git log --all --name-only`, and object-size inspection through `git rev-list --objects --all` with `git cat-file --batch-check`. Pattern hits were manually classified from paths and synthetic contracts without reproducing sensitive-looking values.

Launch disposition at the audited remediation head: clean. A verified secret, credential, or material private artifact in reachable history would block publication and require separately approved safe remediation; deleting only the current copy would be insufficient.