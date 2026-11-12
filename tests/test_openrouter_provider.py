import json

import httpx
import pytest

from marketing_analyzer.llm.openrouter_provider import OpenRouterAuthenticationError, OpenRouterConfigurationError, OpenRouterProvider, OpenRouterResponseError


def test_openrouter_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(OpenRouterConfigurationError):
        OpenRouterProvider().generate_recommendations([])


def test_openrouter_returns_structured_recommendations() -> None:
    request_body: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        request_body.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '[{"recommendation":"Test"}]'}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenRouterProvider(api_key="test-key", model="openrouter/auto", client=client)
    result = provider.generate_recommendations([{"title": "Finding"}])

    assert result == [{"recommendation": "Test"}]
    assert request_body["model"] == "openrouter/auto"
    assert request_body["messages"][1]["content"] == '[{"title": "Finding"}]'
    client.close()


def test_openrouter_retries_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [httpx.Response(429), httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]})]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    monkeypatch.setattr("marketing_analyzer.llm.openrouter_provider.time.sleep", lambda _: None)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenRouterProvider(api_key="test-key", max_retries=1, client=client)
    assert provider.generate_recommendations({"findings": []}) == []
    client.close()


def test_openrouter_rejects_malformed_response() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []})))
    provider = OpenRouterProvider(api_key="test-key", max_retries=0, client=client)
    with pytest.raises(OpenRouterResponseError, match="invalid recommendation JSON"):
        provider.generate_recommendations({"findings": []})
    client.close()


def test_openrouter_authentication_error_does_not_expose_key() -> None:
    secret = "sk-or-secret-test-value"
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(401)))
    provider = OpenRouterProvider(api_key=secret, max_retries=0, client=client)
    with pytest.raises(OpenRouterAuthenticationError) as error:
        provider.generate_recommendations({"findings": []})
    assert "401" in str(error.value)
    assert secret not in str(error.value)
    client.close()
