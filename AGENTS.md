# Repository instructions

This repository implements a vendor-neutral benchmark for engineering-control guarantees around coding-agent stacks.

- Preserve the authority hierarchy documented in `docs/charter.md`.
- Keep examples synthetic and domain-neutral.
- Adapters may translate, launch, observe, normalize, and collect; they must not add controls or score runs.
- Keep functional success separate from control success.
- Prefer externally observed deterministic evidence and never let an agent assertion alone satisfy an oracle.
- M1 remains the deterministic reference baseline. M2 adds only the scoped OpenAI Codex
  AUTH-001 vertical slice; do not infer support for other real hosts or scenarios.
- Never run live Codex trials from normal tests or GitHub Actions, and never persist host
  credentials in fixtures, evidence, manifests, or repository files.
- Update `docs/execution/m1-reference.md` when changing M1 lifecycle state.
- Update `docs/execution/m2-codex.md` when changing M2 lifecycle state; do not rewrite M1
  history.
