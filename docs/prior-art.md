# Prior art and provenance

The project combines established ideas and does not claim ownership of them. This list is representative, not a novelty survey or endorsement.

- Deterministic evaluation and reproducible test fixtures are established software-testing practice; [pytest](https://docs.pytest.org/) is the M1 test harness.
- Supply-chain provenance and subject binding have mature precedent in [SLSA provenance](https://slsa.dev/spec/v1.0/provenance) and [in-toto](https://in-toto.io/). M1 does not implement either standard.
- Trace/event vocabulary has extensive precedent in [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/) and [W3C PROV](https://www.w3.org/TR/prov-overview/). M1 deliberately defines only minimal internal evidence fields.
- Dependency graphs and selective rebuilding/invalidation are foundational build-system concepts; see the [GNU make manual](https://www.gnu.org/software/make/manual/html_node/Introduction.html).
- Isolated concurrent development has long-standing support in [Git worktrees](https://git-scm.com/docs/git-worktree). The benchmark does not require worktrees as the mechanism.
- Secure-development verification and evidence expectations have broad precedent in the [NIST Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final).
- Risk and governance controls for AI systems have broad precedent in the [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework).
- Benchmarking coding agents has major prior art including [SWE-bench](https://www.swebench.com/). This project addresses a different unit of analysis: engineering controls around an agent stack.
- Persistent task state, durable execution, independent review, evidence-gated completion, proof-of-done patterns, context-loss recovery, incident-derived evaluations, risk-proportionate review, agentic control planes, and multi-agent orchestration all predate this repository across workflow systems, CI/CD, safety engineering, and agent frameworks.

No third-party benchmark data or source text is copied here. References are links and short characterizations. The proposed contribution—a vendor-neutral adversarial conformance framework for control guarantees around coding-agent stacks—remains a hypothesis pending evidence.
