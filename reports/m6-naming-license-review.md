# M6 naming and licensing review

Date: 2026-08-29

## Naming check

The launch review searched the exact title `Agentic Engineering Conformance`, the repository/package slug `agentic-engineering-conformance`, and broader web usage.

- GitHub repository search returned only the current private repository for the exact title and slug.
- PyPI returned HTTP 404 for the exact distribution slug at review time.
- General web search found substantial use of the broader phrase `agentic engineering`, but no discovered project using the exact combined title.
- `AEC` is a heavily reused acronym across unrelated fields and should not be promoted as a standalone distinctive brand.

Disposition: no discovered blocking collision for an alpha under the full name and exact slug. Retain the name, avoid an acronym-led brand, and recheck before package publication or a later stable release. This is a dated practical search, not trademark clearance or legal certainty.

## Licensing decision

Use Apache-2.0 for the entire repository: executable code, schemas, scenario definitions, synthetic fixtures, authored benchmark data, documentation, reports, examples, and contributed scenarios. No copied third-party dataset or source text was identified at this stage, so no third-party notice or mixed content license is necessary.

Primary references: GitHub repository search, `https://pypi.org/pypi/agentic-engineering-conformance/json`, [Apache License 2.0](../LICENSE), and [repository licensing policy](../docs/licensing.md).