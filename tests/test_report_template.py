from pathlib import Path

from marketing_analyzer.pipeline import run_analysis
from marketing_analyzer.reporting.html_report import write_html


ROOT = Path(__file__).parents[1]


def test_dashboard_renders_actual_kpis_and_provenance(tmp_path: Path) -> None:
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path)
    html = (tmp_path / "marketing_report.html").read_text(encoding="utf-8")
    assert "Total spend" in html
    assert "$6680" in html
    assert "Total impressions (28d)" in html
    assert "254900" in html
    assert report["provenance"]["ads"]["sha256"] in html
    assert "recommendations-v2" in html
    assert "@media print" in html
    assert "viewport" in html


def test_dashboard_escapes_csv_text_and_handles_empty_recommendations(tmp_path: Path) -> None:
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path)
    report["recommendations"] = []
    report["insights"][0]["title"] = "<script>alert('unsafe')</script>"
    path = tmp_path / "escaped.html"
    write_html(report, path)
    html = path.read_text(encoding="utf-8")
    assert "<script>alert('unsafe')</script>" not in html
    assert "&lt;script&gt;alert(&#39;unsafe&#39;)&lt;/script&gt;" in html
    assert "No AI recommendations are available" in html


def test_review_states_are_visually_distinct(tmp_path: Path) -> None:
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path)
    report["recommendations"] = [
        {"recommendation_id": status, "title": status, "description": "d", "priority": "High", "related_finding_ids": ["ads-0-high-roas"], "evidence": ["e"], "suggested_action": "a", "expected_business_outcome": "o", "measurement_method": "m", "implementation_effort": "Low", "confidence": "high", "review_status": status, "reviewer_note": ""}
        for status in ("pending_review", "approved", "rejected", "needs_revision")
    ]
    path = tmp_path / "review-states.html"
    write_html(report, path)
    html = path.read_text(encoding="utf-8")
    for status in ("review-pending_review", "review-approved", "review-rejected", "review-needs_revision"):
        assert status in html
