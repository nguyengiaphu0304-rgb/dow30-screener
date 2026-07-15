from pathlib import Path

from dow30_screener.demo import main, render_demo_report

EXPECTED = Path(__file__).parents[1] / "docs/demo/walk-forward-report.json"


def test_release_demo_matches_reviewed_artifact_byte_for_byte() -> None:
    assert render_demo_report() == EXPECTED.read_text(encoding="utf-8")


def test_demo_cli_writes_requested_output(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "report.json"
    assert main(("--output", str(output))) == 0
    assert output.read_text(encoding="utf-8") == EXPECTED.read_text(encoding="utf-8")
