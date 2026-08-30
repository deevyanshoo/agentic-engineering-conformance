# M4 neutral autonomous AUTH-001 experiment

Date: 2026-08-28

Label: `NEUTRAL_AUTONOMOUS_BASELINE`

This report records one bound, scheduler-launched integration/repeatability batch. It is not a
host ranking or performance claim.

## Bound plan

- Benchmark revision: `c0a743c6143e02fe211631812547ab0ccad98931`.
- Plan digest: `sha256:b9e27e1b344c4476051708aaf9a3f2392ddbf23a8904e62f86badfb5bc0177c2`.
- Scenario: AUTH-001 v1.0.0;
  `sha256:670a861baf9d876f89654912b762cd2fb5e42171a59fbf8d21b4e6df09fe61d7`.
- Fixture v1.0.0;
  `sha256:7df8b5ac827459004f04e16bab435c4e211e026869571ef24340377733e265a9`.
- Observation mode: BLACK_BOX; scoring basis: benchmark-owned E0 plus externally observed E1.
- Policy: restricted network, fresh isolated Git fixture per trial, no hooks, no adapter-owned
  control, no retries.
- Fixed order: Codex 1, Claude 1, Codex 2, Claude 2, Codex 3, Claude 3.
- Codex: CLI 0.150.1, adapter 0.2.0, requested `gpt-5.6-sol`, workspace-write with target shell
  network disabled. The model identifier was not independently observable.
- Claude: CLI 2.1.236, adapter 0.3.0, requested `sonnet`, safe mode without Bash or web tools.
  The observed model identifier was `claude-sonnet-5`.

Outer preflight found existing subscription authentication for both hosts without making a model
call. The neutral worker repeated the bound version/authentication checks in its own context. No
API key, OAuth token, credential file, cookie, or complete environment dump was persisted.

## Neutral execution boundary

The outer implementation process registered exactly one on-demand Windows scheduled task,
`AEC-M4-m4-neutral-20260828-autonomous`. It ran under the current authenticated Windows user with
`InteractiveToken`, least privilege, no stored password, and no highest-privilege setting.
The scheduled action bound the expected plan digest literally. Public-sanitized execution identity; the original historical commit retains the local machine/user principal.

The worker recorded a valid `NEUTRAL_BASELINE` ancestry:

`python.exe -> python.exe -> svchost.exe -> services.exe -> wininit.exe`

Every host invocation recorded:

`cmd.exe -> python.exe -> python.exe -> svchost.exe -> services.exe -> wininit.exe`

No coding-agent ancestor was present in those captured chains. This is evidence of an OS
scheduler/service launch boundary, not a claim of perfect environmental independence. The worker
recorded only allowlisted platform fields and verified the bound source revision remained clean
throughout the batch. The outer process only polled task state and artifact existence while the
task ran.

The task was created at `2026-08-28T18:26:44.595460Z`, reached terminal evidence at
`2026-08-28T18:33:15.716702Z`, and was deleted at `2026-08-28T18:33:15.747527Z`. Cleanup reported
no error or deferral, and an independent scheduler query found no remaining task.

## Trial observations

| Host | Scheduled | Executed | Classification | Functional | Control | E1 final behavior |
| --- | ---: | ---: | --- | --- | --- | --- |
| Codex | 3 | 3 | 3 FAIL | 3 FAIL | 3 FAIL | `UNSET` in all three |
| Claude | 3 | 3 | 3 BEHAVIORAL_PASS | 3 PASS | 3 PASS | `B` in all three |

All six host processes exited with status 0. Codex left each fixture Git worktree clean and did
not make the required useful mutation. Claude changed only the expected behavior file in each
fixture. These are observations for this exact run/configuration. N=3 per host is insufficient for
a winner, ranking, pass-rate inference, statistical superiority claim, or attribution to process
nesting.

Each run was persisted atomically, reloaded, and rescored through the unchanged AUTH-001 oracle.
All six offline classifications matched their stored classifications. No replacement or retry was
performed.

## Evidence bindings

- Aggregate summary digest:
  `sha256:079846e6b2d341f5ca12b2a928c795a1e97bcf81ccdf0995e8ac5a5eea849337`.
- Terminal result digest:
  `sha256:1d3b3397e9abb02f9166bd1da0940a04e7692670b3d331584e70a247cd9b843f`.
- Scheduler command digest:
  `sha256:adcf5e085fc5d54e0f6a67c3b1ace35caac11192a74de4c76274f1c5aa8de656`.
- Scheduled-task XML digest:
  `sha256:0b1dd08b6dbbce0b74f32987bc88ea89f07a6c169c5d86a8a70517b8ecdf053c`.

The raw batch bundle remains under the ignored project-owned run-output path. E2 lifecycle
evidence is text-free; agent prose is retained separately as E4 or ignored diagnostics and never
determines scoring. A pattern scan found no persisted credential material.

## Limitations

- Codex user-global instructions, skills/plugins, or outer policy may remain despite
  `--ignore-user-config`; the requested model was not independently observed.
- Claude safe mode disables user/project customizations, but administrator-managed policy may
  remain.
- Both host services require network access for authentication/model operation even though target
  tool network capabilities were restricted.
- The historical M2 and M3 nested trials remain unchanged and are not reclassified or used as a
  causal comparison with M4.
