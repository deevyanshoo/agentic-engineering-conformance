import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_public_authority_documents_have_no_writer_artifacts() -> None:
    charter = (ROOT / "docs/charter.md").read_text(encoding="utf-8")
    adr = (ROOT / "docs/decisions/0002-public-alpha-policy.md").read_text(encoding="utf-8")

    assert "\n+" not in charter
    assert "$adr" not in charter
    assert adr.startswith("# ADR 0002: Public alpha policy\n")
    assert len(adr) > 500


def test_sanitized_historical_commands_are_labeled_as_derivatives() -> None:
    m2 = (ROOT / "docs/execution/m2-codex.md").read_text(encoding="utf-8")
    m3 = (ROOT / "reports/m3-claude-live.md").read_text(encoding="utf-8")

    assert "Public-sanitized executable display" in m2
    assert "Public-sanitized ordered argv" in m3
    assert "original historical commit retains the local absolute path" in m2
    assert "original historical commit retains the local absolute path" in m3


def test_public_markdown_has_no_literal_shell_newline_artifacts() -> None:
    paths = (
        ROOT / "docs/charter.md",
        ROOT / "docs/decisions/0002-public-alpha-policy.md",
        ROOT / "docs/execution/m6-public-alpha-readiness.md",
        ROOT / "reports/m6-privacy-history-audit.md",
    )
    for path in paths:
        assert "`r`n" not in path.read_text(encoding="utf-8"), path


def test_launch_validation_public_derivatives_are_sanitized_and_nonranking() -> None:
    report = (ROOT / "reports/m6-launch-validation.md").read_text(encoding="utf-8")
    summary = (ROOT / "reports/m6-launch-validation-summary.json").read_text(encoding="utf-8")
    combined = (report + summary).lower()

    assert "c:\\users\\" not in combined
    assert "execution_identity" not in combined
    assert "scheduled-task.xml" not in combined
    assert ".jsonl" not in combined
    for prohibited in (" winner", " beats ", "safer than", "superiority"):
        assert prohibited not in combined


def test_public_release_surface_is_complete() -> None:
    ci = (ROOT / "docs/ci.md").read_text(encoding="utf-8")
    release = (ROOT / "docs/releases/v0.1.0-alpha.1.md").read_text(encoding="utf-8")

    assert "no live host trials" in ci.lower()
    assert "hosted ci success is not claimed" in ci.lower()
    assert "v0.1.0-alpha.1" in release
    assert "draft" in release.lower()
    assert "AUTH-001 v1" in release
    assert "AUTH-001 v2" in release


def test_public_launch_review_remediations_remain_present() -> None:
    m4_docs = (
        ROOT / "docs/execution/m4-neutral-experiments.md",
        ROOT / "reports/m4-neutral-autonomous.md",
    )
    principal = re.compile(r"\b(?:desktop|laptop)-[a-z0-9-]+\\{1,2}[a-z0-9._-]+\b", re.I)
    for path in m4_docs:
        text = path.read_text(encoding="utf-8")
        assert principal.search(text) is None, path
        assert "Public-sanitized execution identity" in text, path

    architecture = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    release = (ROOT / "docs/releases/v0.1.0-alpha.1.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    clean_clone = (ROOT / "reports/m6-clean-clone.md").read_text(encoding="utf-8")

    assert "remain experimentally unresolved until" not in architecture
    assert "this project's initial vendor-neutral reference vertical slice" in release
    assert "python -m ruff format --check ." in workflow
    assert "workflow_dispatch:" in workflow
    assert "version-pinned AUTH-001 v1" in readme
    assert "documented deterministic gates" in clean_clone
