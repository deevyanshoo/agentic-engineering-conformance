# Repository instructions

This repository implements a vendor-neutral benchmark for engineering-control guarantees around coding-agent stacks.

- Preserve the authority hierarchy documented in `docs/charter.md`.
- Keep examples synthetic and domain-neutral.
- Adapters may translate, launch, observe, normalize, and collect; they must not add controls or score runs.
- Keep functional success separate from control success.
- Prefer externally observed deterministic evidence and never let an agent assertion alone satisfy an oracle.
- M1 remains the deterministic reference baseline. M2 adds only the scoped OpenAI Codex
  AUTH-001 vertical slice; do not infer support for other real hosts or scenarios.
- M3 adds only the scoped Claude Code AUTH-001 vertical slice on top of M2; it is not a
  cross-host performance comparison and does not expand scenario support.
- Never run live Codex or Claude trials from normal tests or GitHub Actions, and never persist
  host credentials in fixtures, evidence, manifests, or repository files.
- Update `docs/execution/m1-reference.md` when changing M1 lifecycle state.
- Update `docs/execution/m2-codex.md` when changing M2 lifecycle state; do not rewrite M1
  history.
- Update `docs/execution/m3-claude.md` when changing M3 lifecycle state; keep M3 stacked on
  M2 until PR #1 is merged or explicitly retargeted.
- M4 live trials may run only from the committed neutral worker launched by the approved
  current-user Windows Task Scheduler boundary. Normal tests, the outer implementation process,
  and GitHub Actions must never invoke them.
- Update `docs/execution/m4-neutral-experiments.md` for M4 state. Keep M4 stacked on M3, preserve
  historical M2/M3 trial records, persist no credentials, and make no host ranking from N=3.
- Update `docs/execution/m5-auth-construct-validity.md` for M5 state. Preserve AUTH-001 v1 and all historical bundles; AUTH v2 and calibration must remain versioned, non-ranking, and independently replayable.
- Update `docs/execution/m6-public-alpha-readiness.md` for M6 state. Keep M6 stacked on M5 and the repository PRIVATE until explicit founder publication authorization. Do not merge, tag, release, or change visibility while preparing `PUBLIC_ALPHA_READY`.
- Public artifacts must exclude credentials, raw prose-bearing host diagnostics, private reasoning, and unnecessary machine-identifying environment data. Ordinary deterministic contributor checks must not require paid model access.