# Contributing adapters

Adapters translate, launch, observe, normalize, collect, and clean up. They do not decide results or improve the stack under test.

## Required boundary

Implement the existing `probe`, `prepare`, `execute`, `collect`, and `cleanup` interface. Capability negotiation happens before execution; scenario oracles own scoring.

An adapter must not secretly install a blocking hook, lock, review requirement, verification/completion gate, authority policy, hidden answer, or prompt hint. A control intentionally under test belongs to the declared stack configuration.

## Isolation and evidence

- Execute targets only in dedicated synthetic Git fixtures, never in this repository or an unrelated checkout.
- Do not copy credentials; use existing host authentication through the supported CLI surface.
- Capture final E1 state independently of agent assertions.
- Keep E2 minimal and text-free. Agent prose is E4 or ignored diagnostics; private reasoning is never collected.
- Preserve unknown structured events safely where possible, and fail soundly on malformed required output.
- Cleanup must not follow links/reparse points or rewrite persisted results.

## Deterministic tests

Use an injected process seam; normal tests must never spend quota. Cover missing executable/auth capability, version parsing, exact command construction, sandbox/permissions, timeout, non-zero exit, malformed/unknown events, missing E1, containment, cleanup, raw diagnostic separation, persistence, and offline rescore. Add a cross-host contract test rather than host-specific benchmark semantics.

Live validation is maintainer-operated and optional. See [CONTRIBUTING.md](../CONTRIBUTING.md) and [public evidence policy](evidence-policy.md).