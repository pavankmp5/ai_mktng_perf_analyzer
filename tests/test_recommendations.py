from pathlib import Path

import pytest

from marketing_analyzer.llm.endpoints import EndpointRegistry
from marketing_analyzer.llm.recommendation_engine import build_action_plan
from marketing_analyzer.pipeline import run_analysis


ROOT = Path(__file__).parents[1]


def test_normal_pipeline_keeps_recommendations_disabled(tmp_path: Path) -> None:
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path)
    assert report["recommendations_status"] == "disabled"
    assert report["recommendations"] == []


def test_explicit_recommendations_without_key_are_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path, recommendations=True)
    assert report["recommendations_status"] == "skipped_due_to_configuration"
    assert report["insights"]


def test_endpoint_registry_exposes_named_profiles() -> None:
    registry = EndpointRegistry()
    assert {"openrouter_default", "openai_direct", "gemini_direct", "custom_openai_compatible"}.issubset(registry.names())
    assert registry.get("gemini_direct").provider == "gemini"
    with pytest.raises(ValueError, match="Unknown LLM endpoint profile"):
        registry.get("missing")


def test_recommendations_are_validated_and_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProvider:
        def generate_recommendations(self, context: dict) -> list[dict]:
            finding = context["findings"][0]["finding_id"]
            return [{
                "recommendation_id": "rec-1", "title": "Improve priority finding", "category": "SEO",
                "description": "Use the measured finding as the optimization starting point.",
                "related_finding_ids": [finding], "priority": "High", "evidence": ["Measured finding"],
                "suggested_action": "Review the relevant page or campaign.",
                "expected_business_outcome": "Improve the measured KPI.",
                "measurement_method": "Compare the same KPI on the next run.", "implementation_effort": "Medium",
                "confidence": "medium", "assumptions": ["The finding remains relevant."],
                "limitations": ["No historical data is available."],
            }]

    monkeypatch.setattr("marketing_analyzer.pipeline.create_provider", lambda profile, model=None: FakeProvider())
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path, recommendations=True)
    assert report["recommendations_status"] == "generated"
    assert report["recommendations"][0]["recommendation_id"] == "rec-1"
    assert (tmp_path / "marketing_report.json").exists()
    assert (tmp_path / "marketing_report.html").exists()


def test_malformed_provider_response_preserves_deterministic_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProvider:
        def generate_recommendations(self, context: dict) -> list[dict]:
            return [{"unexpected": "shape"}]

    monkeypatch.setattr("marketing_analyzer.pipeline.create_provider", lambda profile, model=None: FakeProvider())
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path, recommendations=True)
    assert report["recommendations_status"] == "failed"
    assert report["recommendations"] == []
    assert report["ads"]["row_count"] == 10
    assert "0.recommendation_id (missing)" in report["recommendations_error"]
    assert "shape" not in report["recommendations_error"]


def test_provider_and_endpoint_conflict_is_reported_without_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    report = run_analysis(
        ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path,
        recommendations=True, llm_provider="openai", llm_endpoint="openrouter_default",
    )
    assert report["recommendations_status"] == "skipped_due_to_configuration"
    assert report["recommendations_error"] == "LLM provider or endpoint configuration is invalid."
    assert report["insights"]


def test_action_plan_orders_by_priority_then_effort() -> None:
    recommendations = [
        {"recommendation_id": "r-medium", "priority": "Medium", "implementation_effort": "Low"},
        {"recommendation_id": "r-critical", "priority": "Critical", "implementation_effort": "Medium"},
        {"recommendation_id": "r-high", "priority": "High", "implementation_effort": "Low"},
        {"recommendation_id": "r-low", "priority": "Low", "implementation_effort": "Low"},
    ]
    plan = build_action_plan(recommendations)
    assert [item["recommendation_id"] for item in plan["immediate_actions"]] == ["r-critical", "r-high"]
    assert [item["recommendation_id"] for item in plan["short_term_optimisation"]] == ["r-medium"]
    assert [item["recommendation_id"] for item in plan["longer_term_opportunities"]] == ["r-low"]
