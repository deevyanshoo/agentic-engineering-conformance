# M6 Public Alpha Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a private, verified `v0.1.0-alpha.1` launch candidate and exact publication plan without merging, tagging, releasing, or changing visibility.

**Architecture:** Reuse M1-M5 and the neutral paired-experiment path. Add launch-facing documentation, policy, verification evidence, and only narrowly justified test-first corrections. Preserve historical results and stage M6 above M5.

**Tech Stack:** Python 3.11+, JSON Schema, pytest, Ruff, strict mypy, Git/GitHub, Windows Task Scheduler.

## Global Constraints

- Keep the repository PRIVATE and all PRs unmerged through `PUBLIC_ALPHA_READY`.
- Do not create or push `v0.1.0-alpha.1`; prepare metadata only.
- Add no hosts, domains, dashboards, services, rankings, or speculative runtime features.
- Persist no credentials, prose-bearing raw host transcripts, or private reasoning.
- Execute live trials only through the committed current-user Task Scheduler boundary.
- Preserve M1-M5 records and the terminally invalid M5 batch unchanged.

### Task 1: Authority and launch state

- [ ] Persist exact Git/GitHub/PR/CI/baseline evidence in the M6 execution record and AGENTS.md.
- [ ] Inspect, run `git diff --check`, and commit the authority checkpoint.

### Task 2: Positioning, claims, provenance, and licensing

- [ ] Research current naming collisions and public prior art; record URLs and limitations.
- [ ] Rewrite README, claims, prior art, licensing, evidence policy, roadmap, NOTICE, and version metadata.
- [ ] Scan for novelty/ranking overclaims, verify whitespace, and commit.

### Task 3: Contributor, security, and community experience

- [ ] Add CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, scenario/adapter guides, issue templates, and PR template.
- [ ] Separate deterministic contributor gates from optional maintainer live-host validation.
- [ ] Validate paths/templates and commit.

### Task 4: Current-tree and complete-history audit

- [ ] Scan current tree and every reachable candidate commit for credentials, private data, transcripts, artifacts, the founder-supplied private-project sentinel, and proprietary terms.
- [ ] Distinguish public authorship/harmless paths from secrets; stop on material contamination.
- [ ] Verify ignored outputs are untracked, record dispositions, and commit.

### Task 5: Successor experiment pre-live gate

- [ ] Run Ruff, mypy, pytest/schema, branch-range checks, auth preflight, and clean-source verification.
- [ ] Prepare a new exact twelve-slot paired zero-retry design.
- [ ] Obtain independent pre-live review, remediate blockers, and commit GO evidence before binding.

### Task 6: Neutral launch-validation batch

- [ ] Bind the immutable plan to the clean commit and launch once through Task Scheduler.
- [ ] Monitor without source mutation/intervention.
- [ ] Reconcile slots, ancestry, auth, retries, evidence/rescores, aggregate, cleanup, and source state.
- [ ] Commit a conservative sanitized report while preserving M5 unchanged.

### Task 7: Clean-clone and CI strategy

- [ ] Clone the exact candidate into a temporary directory.
- [ ] Follow documented install, Ruff, mypy, pytest/schema, reference, and rescore commands only.
- [ ] Record results, remove the clone, and document the truthful hosted-CI gate.

### Task 8: Alpha metadata, reviews, and closure

- [ ] Prepare `0.1.0a1` / `v0.1.0-alpha.1` metadata without a tag.
- [ ] Obtain fresh engineering and public/claims reviews; remediate blockers.
- [ ] Run final deterministic, audit, clean-clone, and branch-range gates.
- [ ] Push M6, open a draft PR targeting M5, verify private/no tag/no release.
- [ ] Record exact PR #1 -> #2 -> #3 -> #4 -> M6 integration and stop at `PUBLIC_ALPHA_READY`.