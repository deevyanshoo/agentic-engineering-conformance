# Prior art and provenance

This project combines established ideas and does not claim ownership of them. The list is representative, dated for the alpha, and neither a novelty survey nor an endorsement.

## Engineering methods and agent workflows

- [Proof-or-Stop](https://github.com/Proof-or-Stop) explores evidence-led stopping and completion practices for agentic work.
- [Agentic Agile-V](https://github.com/Agile-V/agentic_agile_v) provides a verifiable AI-augmented engineering scaffold with briefs, evidence, gates, and traceability.
- [Superpowers](https://github.com/obra/superpowers) is an agentic skills framework and software-development methodology with planning, test, review, and worktree practices.
- [GitHub Spec Kit](https://github.com/github/spec-kit) provides tooling for specification-driven development.
- [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) is an AI-driven development method with structured planning and workflow roles.
- [Agent Skills](https://agentskills.io/specification) defines a portable format for packaging agent instructions and resources. This benchmark does not define another skills format.
- [Beads](https://github.com/gastownhall/beads) addresses durable issue/task memory for coding agents; [Gas Town](https://github.com/gastownhall/gastown) addresses multi-agent workspace orchestration. This project is neither a task tracker nor an orchestrator.

## Verification, provenance, and conformance

- Deterministic fixtures, regression tests, independent review, task graphs, dependency invalidation, isolated Git work, evidence-gated completion, persistent workflow state, and context-loss recovery are established software-engineering concepts.
- [SLSA provenance](https://slsa.dev/spec/v1.0/provenance) and [in-toto](https://in-toto.io/) provide mature supply-chain provenance and subject-binding models. This alpha implements neither standard.
- [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/) and [W3C PROV](https://www.w3.org/TR/prov-overview/) provide extensive trace/provenance vocabulary. The benchmark uses only a small internal evidence model.
- Build systems have long implemented selective dependency invalidation; the [GNU make manual](https://www.gnu.org/software/make/manual/html_node/Introduction.html) is one accessible reference.
- [Git worktrees](https://git-scm.com/docs/git-worktree) are established isolation machinery. The MUT invariant does not prescribe worktrees.

## Benchmarks, security, and governance

- [SWE-bench](https://www.swebench.com/) is major coding-agent capability-benchmark prior art. Agentic Engineering Conformance studies a different unit: engineering controls around the agent stack.
- Incident-derived evaluation, risk-proportionate review, agentic control planes, trace-based evaluation, and multi-agent orchestration predate this repository across CI/CD, safety engineering, workflow systems, and agent frameworks.
- The [NIST Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final), [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework), and [OWASP Agentic Security Initiative](https://genai.owasp.org/initiatives/agentic-security-initiative/) provide relevant secure-development and AI-risk context. This benchmark does not implement or certify conformance with them.

No third-party benchmark data, prompts, or source text are copied here. Links and concise factual descriptions provide attribution. The proposed vendor-neutral adversarial framing remains a hypothesis whose usefulness must be established by evidence.