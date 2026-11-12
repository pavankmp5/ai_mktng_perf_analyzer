import pandas as pd
import pytest

from marketing_analyzer.insights.rules import build_insights
from marketing_analyzer.insights.scoring import ScoringWeights, priority_for_score, score_factors
from marketing_analyzer.llm.recommendation_engine import RecommendationValidationError, build_action_plan, validate_recommendations


def test_scoring_is_bounded_explainable_and_configurable() -> None:
    weights = ScoringWeights(40, 20, 20, 10, 10)
    assert score_factors({"potential_business_impact": 100, "financial_exposure_or_opportunity": 0}, weights) == 66.67
    assert score_factors({"potential_business_impact": None, "financial_exposure_or_opportunity": 100}, weights) == 100
    assert priority_for_score(80) == "Critical"
    assert priority_for_score(60) == "High"
    assert priority_for_score(35) == "Medium"
    assert priority_for_score(34.99) == "Low"


def test_rules_trace_ads_and_seo_entities_without_historical_claims() -> None:
    ads = pd.DataFrame([
        {"campaign": "A", "spend_usd": 1000, "clicks": 10, "purchases": 1, "revenue_usd": 100, "impressions": 1000, "reach": 500},
        {"campaign": "B", "spend_usd": 10, "clicks": 100, "purchases": 10, "revenue_usd": 100, "impressions": 1000, "reach": 500},
    ])
    seo = pd.DataFrame([
        {"product_id": "p1", "url_slug": "/one", "impressions_28d": 1000, "clicks_28d": 1, "avg_position": 30, "indexed": False, "page_load_ms": 500},
        {"product_id": "p2", "url_slug": "/two", "impressions_28d": 10, "clicks_28d": 2, "avg_position": 1, "indexed": True, "page_load_ms": 50},
    ])
    findings = build_insights(ads, seo)
    assert findings
    assert all(item["evidence"] and "source row" in item["evidence"][0] for item in findings)
    assert any(item["entity_name"] == "A" and item["type"] == "problem" for item in findings)
    assert any(item["entity_name"] == "/one" and "not-indexed" in item["finding_id"] for item in findings)
    assert all("historical" not in item["description"].lower() for item in findings)


def test_recommendation_validation_rejects_unknown_finding_reference() -> None:
    recommendation = {"recommendation_id": "r1", "title": "T", "category": "SEO", "description": "D", "related_finding_ids": ["missing"], "priority": "High", "evidence": ["E"], "suggested_action": "A", "expected_business_outcome": "O", "measurement_method": "M", "implementation_effort": "Low", "confidence": "high", "assumptions": ["X"], "limitations": ["L"]}
    with pytest.raises(RecommendationValidationError, match="unknown finding IDs"):
        validate_recommendations([recommendation], {"known"})


def test_action_plan_groups_without_deadlines() -> None:
    recommendations = [
        {"recommendation_id": "a", "title": "A", "priority": "Critical", "implementation_effort": "Low"},
        {"recommendation_id": "b", "title": "B", "priority": "Medium", "implementation_effort": "Medium"},
        {"recommendation_id": "c", "title": "C", "priority": "Low", "implementation_effort": "High"},
    ]
    plan = build_action_plan(recommendations)
    assert [item["title"] for item in plan["immediate_actions"]] == ["A"]
    assert [item["title"] for item in plan["short_term_optimisation"]] == ["B"]
    assert [item["title"] for item in plan["longer_term_opportunities"]] == ["C"]
    assert "202" not in plan["ordering_reason"]
