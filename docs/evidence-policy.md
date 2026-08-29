# Public evidence and privacy policy

## Public by default

- scenario definitions, schemas, deterministic synthetic fixtures, and oracle rules;
- source code and deterministic tests;
- synthetic reference evidence and safe example bundles;
- sanitized run manifests, plan/result digests, and aggregate summaries;
- methodology, decisions, execution records, limitations, and review summaries; and
- provenance and prior-art citations.

## Not public by default

- raw host transcripts or conversation exports;
- prose-bearing Codex/Claude JSONL diagnostics;
- authentication artifacts, OAuth tokens, API keys, cookies, or credential files;
- complete environment dumps, unnecessary machine identifiers, or local scheduler internals;
- private chain-of-thought or model reasoning; and
- ignored run workspaces, caches, logs, or temporary files.

E2 lifecycle evidence is intentionally text-free. Agent prose and assertions are E4 or ignored diagnostics and cannot determine a deterministic score. A maintainer may publish a sanitized derivative of a historical record, but must retain its identity/digest relationship, state every redaction, and never rewrite the original as if the public form were what originally existed.

Before accepting contributed evidence, reviewers must verify scenario and fixture binding, provenance level, subject identity, absence of credentials and unnecessary personal data, and that any external content may legally be redistributed. Full transcripts are never required for conformance.