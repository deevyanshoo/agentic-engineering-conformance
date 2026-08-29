# M6 clean-clone reproduction

Date: 2026-08-29

Revision tested: `dc33e29f70948d83f0ebb4405d12cf6ddcf36721`

A fresh local clone was created in a newly generated system temporary directory with `git clone --no-local --branch m6/public-alpha-readiness`. The initial checkout was clean. A new virtual environment was created and only the documented deterministic quickstart commands were used.

| Command | Outcome |
| --- | --- |
| `python -m pip install -e ".[dev]"` | PASS; package `0.1.0a1` installed from the clone |
| `python -m ruff format --check .` | PASS; 117 files already formatted |
| `python -m ruff check .` | PASS |
| `python -m mypy --strict src` | PASS; 27 source files |
| `python -m pytest -q` | PASS; 241 tests in 49.46 seconds |
| `python -m agentic_conformance.reference_demo --output reference-evidence.json` | PASS; `GUARDED_PASS`, functional/control `PASS`, offline rescore equal |

The only untracked file after execution was the intentionally generated synthetic `reference-evidence.json`. No Codex or Claude host process was invoked. The exact validated temporary clone was removed after the gate.