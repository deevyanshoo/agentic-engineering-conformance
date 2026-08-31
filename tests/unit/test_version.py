import tomllib
from pathlib import Path

import agentic_conformance

ROOT = Path(__file__).parents[2]


def test_alpha_version_metadata_is_consistent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == "0.1.0a2"
    assert agentic_conformance.__version__ == "0.1.0a2"
