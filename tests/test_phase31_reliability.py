import json
from pathlib import Path

import httpx
import pytest

from marketing_analyzer.llm.errors import RecommendationErrorCategory
from marketing_analyzer.llm.openrouter_provider import OpenRouterResponseError, OpenRouterProvider
from marketing_analyzer.llm.prompts import PROMPT_VERSION, build_recommendation_messages
from marketing_analyzer.llm.review import ReviewDecision, apply_review_decisions, load_review_decisions, recommendation_fingerprint, save_review_decision


def test_prompt_version_and_construction_are_stable() -> None:
    messages = build_recommendation_messages({"findings": [{"finding_id": "f1"}]})
    assert PROMPT_VERSION == "recommendations-v2"
    assert messages[0]["role"] == "system"
    assert "related_finding_ids" in messages[0]["content"]
    assert "must be non-empty" in messages[0]["content"]
    assert 'confidence":"medium"' in messages[0]["content"]
    assert json.loads(messages[1]["content"])["findings"][0]["finding_id"] == "f1"


@pytest.mark.parametrize(("status", "category"), [(402, RecommendationErrorCategory.INSUFFICIENT_CREDITS), (404, RecommendationErrorCategory.MODEL_UNAVAILABLE), (429, RecommendationErrorCategory.RATE_LIMIT)])
def test_provider_classifies_http_failures(status: int, category: RecommendationErrorCategory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("marketing_analyzer.llm.openrouter_provider.time.sleep", lambda _: None)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    provider = OpenRouterProvider(api_key="test-key", max_retries=0, client=client)
    with pytest.raises(OpenRouterResponseError) as error:
        provider.generate_recommendations({"findings": []})
    assert error.value.category == category
    client.close()


def test_provider_classifies_empty_and_invalid_json() -> None:
    for content, category in [("", RecommendationErrorCategory.EMPTY_RESPONSE), ("not json", RecommendationErrorCategory.INVALID_JSON)]:
        client = httpx.Client(transport=httpx.MockTransport(lambda request, content=content: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})))
        provider = OpenRouterProvider(api_key="test-key", max_retries=0, client=client)
        with pytest.raises(OpenRouterResponseError) as error:
            provider.generate_recommendations({"findings": []})
        assert error.value.category == category
        client.close()


def test_review_decisions_persist_and_apply(tmp_path: Path) -> None:
    path = tmp_path / "reviews.json"
    recommendation = {"recommendation_id": "r1", "title": "Test"}
    save_review_decision(path, ReviewDecision(recommendation_id="r1", review_status="approved", reviewer_note="Checked evidence", recommendation_fingerprint=recommendation_fingerprint(recommendation)))
    assert load_review_decisions(path)["r1"]["review_status"] == "approved"
    result = apply_review_decisions([recommendation, {"recommendation_id": "r2", "title": "Other"}], path)
    assert result[0]["review_status"] == "approved"
    assert result[1]["review_status"] == "pending_review"


def test_changed_recommendation_does_not_inherit_review(tmp_path: Path) -> None:
    path = tmp_path / "reviews.json"
    original = {"recommendation_id": "r1", "title": "Original"}
    save_review_decision(path, ReviewDecision(recommendation_id="r1", review_status="approved", recommendation_fingerprint=recommendation_fingerprint(original)))
    changed = {"recommendation_id": "r1", "title": "Changed"}
    assert apply_review_decisions([changed], path)[0]["review_status"] == "pending_review"
