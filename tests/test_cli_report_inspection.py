import json
from pathlib import Path

from marketing_analyzer.cli import _inspect_report


def test_inspection_reports_resolved_path_and_optional_fields(tmp_path: Path, capsys) -> None:
    path = tmp_path / "reports" / "marketing_report.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"recommendations_status": "disabled"}), encoding="utf-8")
    assert _inspect_report(path) == 0
    output = capsys.readouterr().out
    assert f"Report path: {path.resolve()}" in output
    assert "File exists: True" in output
    assert "Status: disabled" in output
    assert "Error: None" in output
    assert "Recommendations: 0" in output


def test_inspection_displays_safe_error_details(tmp_path: Path, capsys) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({
        "recommendations_status": "failed",
        "recommendations_error_category": "schema_validation_error",
        "recommendations_error": "LLM recommendations failed schema validation: 0.confidence (string_type)",
    }), encoding="utf-8")
    assert _inspect_report(path) == 0
    output = capsys.readouterr().out
    assert "Details: LLM recommendations failed schema validation: 0.confidence (string_type)" in output


def test_inspection_distinguishes_missing_file(tmp_path: Path, capsys) -> None:
    path = tmp_path / "missing" / "report.json"
    assert _inspect_report(path) == 1
    output = capsys.readouterr().out
    assert "Report not found." in output
    assert f"Expected path: {path.resolve()}" in output
    assert "Check whether report generation completed successfully." in output


def test_inspection_distinguishes_invalid_json(tmp_path: Path, capsys) -> None:
    path = tmp_path / "report.json"
    path.write_text("{not-json", encoding="utf-8")
    assert _inspect_report(path) == 1
    assert "Invalid JSON:" in capsys.readouterr().out


def test_inspection_counts_recommendations_and_handles_zero(tmp_path: Path, capsys) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"recommendations_status": "generated", "recommendations": [{"recommendation_id": "r1", "title": "Test"}]}), encoding="utf-8")
    assert _inspect_report(path) == 0
    output = capsys.readouterr().out
    assert "Recommendations: 1" in output
    assert "r1 [pending_review] Test" in output
