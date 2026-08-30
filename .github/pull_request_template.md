## Purpose

Describe the invariant, defect, or documentation outcome this change addresses.

## Evidence and verification

List exact deterministic commands and outcomes. Ordinary changes must not require paid model access.

## Boundary checks

- [ ] Functional and control outcomes remain separate where applicable.
- [ ] Adapter code does not score or add an engineering control.
- [ ] Historical scenario/evidence replay remains valid, or the change is explicitly versioned.
- [ ] No credential, raw host transcript, private reasoning, proprietary data, or unnecessary machine identifier is included.
- [ ] Ruff format/check, strict mypy, full deterministic pytest, and `git diff --check` pass.
- [ ] Live-host calls were not run, or maintainer authorization and the bound-plan evidence are linked.

## Limitations

State what this change does not establish.