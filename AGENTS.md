# Repository instructions

This repository implements a vendor-neutral benchmark for engineering-control guarantees around coding-agent stacks.

- Preserve the authority hierarchy documented in `docs/charter.md`.
- Keep examples synthetic and domain-neutral.
- Adapters may translate, launch, observe, normalize, and collect; they must not add controls or score runs.
- Keep functional success separate from control success.
- Prefer externally observed deterministic evidence and never let an agent assertion alone satisfy an oracle.
- Do not add real coding-agent adapters during M1.
- Update `docs/execution/m1-reference.md` when changing M1 lifecycle state.

