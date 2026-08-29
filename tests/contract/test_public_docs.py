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
