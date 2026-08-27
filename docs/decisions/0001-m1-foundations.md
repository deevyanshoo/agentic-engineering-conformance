# ADR 0001: M1 foundations

Status: accepted for provisional v0.1. Date: 2026-08-27.

1. **Conformance scope:** build a benchmark around declared engineering-control guarantees, not a new methodology or agent runtime.
2. **Six provisional domains:** use AUTH, MUT, COMP, REV, INV, and REC as a revisable v0.1 taxonomy.
3. **Two pass classes:** distinguish genuinely exercised protection (GUARDED_PASS) from intact behavior without control-exercise proof (BEHAVIORAL_PASS).
4. **Adapter non-intervention:** adapters observe and normalize but do not add controls or score.
5. **Separate dimensions:** persist functional and control outcomes independently.
6. **No composite score:** expose classifications and limitations directly in v0.1.
7. **Evidence preference:** prefer benchmark-owned ground truth and externally observed deterministic evidence; never accept E4 alone.
8. **No chain-of-thought requirement:** score observable durable artifacts; transcripts are optional diagnostics.

Consequences: reference modes validate benchmark plumbing only; scenario oracles own classification; external adapters and weighting remain later decisions.
