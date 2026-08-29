# M6 repository privacy, secret, and contamination audit

Date: 2026-08-29

Exact audited head after pre-live remediation: `0ca1a705c882e3508a79ac10cbc2ba345f51375d`

Scope: the complete M6 working tree (including untracked launch-candidate files) and all 64 commits reachable from local/remote refs across `main` and the M2-M6 stack. Values matching sensitive patterns were never printed; scans reported paths/counts only.

## Current-tree results

- High-confidence token/key/private-key shapes: no matches.
- Credential assignments (`api_key`, OAuth/access token, client secret, password, cookie): no matches.
- Founder-supplied private-project sentinel: no matches.
- Absolute user-home paths: no matches after replacing two unnecessary current-tree historical display paths with `%APPDATA%` forms.
- Email-shaped content: one synthetic `fixture@example.invalid` identity used for isolated Git fixtures.
- Tracked `.env`, key/certificate, JSONL, log, database, archive, executable, or binary artifacts: none.
- Tracked files larger than 1 MiB: none.
- Raw host transcripts or prose-bearing diagnostic sidecars: none tracked. Source/tests mention their exclusion or classification, but do not contain a transcript.
- Ignored cache/build directories are local only; `reports/runs/` and its live artifacts remain ignored and untracked.

## Reachable-history results

- High-confidence token/key/private-key shapes: zero matching commits.
- Credential assignments: zero matching commits.
- Founder-supplied private-project sentinel: zero matching commits.
- Suspicious credential/log/transcript/binary filenames: none reachable.
- Blobs larger than 1 MiB: none reachable.
- Email-shaped file content appears only as the synthetic `example.invalid` fixture identity (including its earlier shared-fixture path).
- One configured Git author identity exists in commit metadata. It is treated as intentional public authorship, not a secret; the email is not duplicated in this report.
- Two harmless Windows executable paths containing the local username occur in older M2/M3 commits. Current public documents use `%APPDATA%`. The old strings contain no credential or secret and preserve historical machine context. A destructive stack-wide history rewrite would add disproportionate provenance risk, so no rewrite is justified.

## Proprietary contamination gate

The sentinel and focused domain scans found no private repository name, customer information, proprietary architecture, financial-product methodology, regulatory reasoning, private roadmap, copied proprietary implementation, or private research. All fixtures are small synthetic engineering states.

Result: **NO PROPRIETARY CONTAMINATION FOUND.**

## Commands and disposition

The audit used `rg` over the complete working tree, `git grep -l` across every `git rev-list --all` commit, filename history from `git log --all --name-only`, and object-size inspection through `git rev-list --objects --all | git cat-file --batch-check`. Pattern hits were manually classified from their paths and synthetic contracts. The exact pattern categories are recorded here without reproducing sensitive-looking values.

Launch disposition: clean. A future verified secret, credential, or material private artifact in reachable history would block publication and require a separately approved safe remediation; deleting only the current copy would be insufficient.