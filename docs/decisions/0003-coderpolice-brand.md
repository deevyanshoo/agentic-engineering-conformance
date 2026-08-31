# Decision 0003 — CoderPolice public brand

Status: accepted

Date: 2026-08-31

## Decision

Use **CoderPolice** as the public project name.

Keep **Agentic Engineering Conformance** as the technical descriptor for the benchmark category and methodology.

Primary public tagline:

> Okay, but prove it.

## Rationale

The original public title accurately described the research programme but read like a standards-paper heading rather than a memorable open-source project. CoderPolice keeps the project clearly tied to coding agents while matching the benchmark's core behavior: engineering claims such as tested, reviewed, done, current, or ready must be justified by admissible evidence.

The brand is intentionally lighter than the underlying methodology. Public copy may use the name and tagline playfully, but benchmark contracts, result semantics, evidence classes, scenario IDs, and domain terminology remain technical and unchanged.

## Naming diligence

Basic public-search diligence found no material exact current GitHub/software/package collision for `CoderPolice` at the time of this decision. This is not legal or trademark clearance.

`AgentPolice` was considered but not selected because exact and strongly adjacent prior uses already exist in agent/security tooling. `StackCop` and other alternatives were rejected on fit rather than technical constraints.

## Historical boundary

- `v0.1.0-alpha.1` remains immutable under the original technical working title.
- M1–M6 milestone records, experiment bundles, PR history, and historical evidence are not rewritten for branding.
- Future public surfaces use CoderPolice while preserving the technical descriptor where useful.
- The Python import namespace remains `agentic_conformance` for now; branding does not justify breaking import paths.
- The distribution metadata may use `coderpolice` beginning with the next alpha because no package-registry publication occurred for alpha.1.
