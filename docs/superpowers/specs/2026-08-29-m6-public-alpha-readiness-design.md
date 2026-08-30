# M6 public alpha readiness design

Date: 2026-08-29

## Objective

Turn the private M1-M5 development stack into one reviewable public-alpha launch candidate without merging, tagging, releasing, or changing repository visibility. A stranger must be able to understand, install, deterministically verify, and contribute while the experimental and non-claim boundaries remain explicit.

## Chosen approach

Use `m6/public-alpha-readiness` stacked from the exact M5 head. Preserve milestone commits and draft PRs, then prepare a bottom-up integration plan rather than rewriting or prematurely merging history. Prefer one repository-wide Apache-2.0 boundary unless the audit establishes a concrete need for another license.

Public hardening is documentation- and verification-led. The README is the external entry point; focused contributor, security, evidence-policy, claims, prior-art, CI, and release documents provide depth. Existing deterministic contracts remain authoritative. Any executable correction must be current-scope and test-first.

## Public evidence boundary

Commit code, schemas, scenarios, synthetic fixtures, sanitized manifests/aggregates, methodology, decisions, and reviews. Exclude raw host transcripts, prose-bearing diagnostics, authentication material, credential stores, environment dumps, private reasoning, and ignored run directories. Preserve historical records; contextualize harmless machine paths rather than silently rewriting them.

Scan the current tree and every reachable candidate commit for secrets, privacy exposure, and proprietary contamination. A verified secret or material proprietary contamination blocks readiness. Public Git authorship and harmless historical paths are assessed and reported rather than mislabeled as secrets.

## Launch-validation experiment

Reuse the M4/M5 digest-bound paired plan, neutral worker, and current-user least-privilege Task Scheduler controller unless a concrete defect appears. Bind a new M6 batch identity to one clean committed revision. Run twelve zero-retry BLACK_BOX slots using AUTH-001 v2 and the no-conflict calibration. This is a successor experiment, not a retry or replacement for M5. Report exact-run evidence only, without host ranking.

A fresh read-only pre-live reviewer must return GO before scheduling. The outer session does not launch hosts directly or edit source during the batch. Reconcile atomic evidence, rescore equality, ancestry, source binding, and task cleanup afterward.

## Reproduction and CI

Separate free deterministic reference verification from optional paid host integration. A clean clone of the exact candidate must pass the documented install, Ruff, strict mypy, full pytest/schema contracts, deterministic reference example, and stored-evidence rescore.

Keep the existing truthful deterministic Actions workflow, but do not claim hosted success while account restrictions prevent steps from starting. Require one public-repository Actions probe after an authorized visibility transition before making a green-CI claim.

## Release boundary

Prepare `v0.1.0-alpha.1` metadata, release notes, two independent launch reviews, a draft M6 PR, and exact sequential integration operations. Stop at `PUBLIC_ALPHA_READY`. Founder authority remains required to merge, change visibility, create/push the tag, or publish a release.