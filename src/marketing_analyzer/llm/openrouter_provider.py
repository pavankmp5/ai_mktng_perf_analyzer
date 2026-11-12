"""OpenRouter implementation using its OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .base_provider import LLMProvider
from .errors import RecommendationErrorCategory
from .prompts import PROMPT_VERSION, build_recommendation_messages


DEFAULT_MODEL = "openrouter/auto"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterConfigurationError(RuntimeError):
    """Raised when OpenRouter cannot be used because configuration is missing."""


class OpenRouterAuthenticationError(RuntimeError):
    """Raised for an authentication failure without exposing credentials."""

    category = RecommendationErrorCategory.AUTHENTICATION_ERROR


class OpenRouterResponseError(RuntimeError):
    """Raised when OpenRouter returns an unusable response."""

    def __init__(self, message: str, category: RecommendationErrorCategory = RecommendationErrorCategory.PROVIDER_ERROR) -> None:
        super().__init__(message)
        self.category = category


@dataclass
class OpenRouterProvider(LLMProvider):
    """Generate structured recommendations through OpenRouter.

    The API key is intentionally read from ``OPENROUTER_API_KEY`` by default.
    It must never be committed to source, ``.env.example``, or CI configuration.
    """

    api_key: str | None = None
    model: str | None = None
    base_url: str = DEFAULT_BASE_URL
    app_name: str = "AI Marketing Performance Analyser"
    http_referer: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2
    temperature: float = 0.2
    response_format: str = "json"
    client: httpx.Client | None = None

    prompt_version: str = PROMPT_VERSION

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = self.model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.base_url = os.getenv("OPENROUTER_BASE_URL", self.base_url).rstrip("/")
        self.app_name = os.getenv("OPENROUTER_APP_NAME", self.app_name)
        self.http_referer = self.http_referer or os.getenv("OPENROUTER_HTTP_REFERER")
        self.response_format = os.getenv("OPENROUTER_RESPONSE_FORMAT", self.response_format)

    def generate_recommendations(self, context: dict | list[dict]) -> list[dict]:
        if not self.api_key:
            raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured")
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": build_recommendation_messages(context),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.app_name,
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer

        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        should_close = self.client is None
        try:
            body = self._request_with_retries(client, headers, payload)
        finally:
            if should_close:
                client.close()

        try:
            content = body["choices"][0]["message"].get("content")
            if not content or not str(content).strip():
                raise OpenRouterResponseError("OpenRouter returned an empty recommendation response", RecommendationErrorCategory.EMPTY_RESPONSE)
            text = str(content).strip()
            if self.response_format == "json_markdown" and text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            recommendations = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenRouterResponseError("OpenRouter returned invalid recommendation JSON", RecommendationErrorCategory.INVALID_JSON) from exc
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise OpenRouterResponseError("OpenRouter returned invalid recommendation JSON", RecommendationErrorCategory.INVALID_JSON) from exc
        if not isinstance(recommendations, list) or not all(isinstance(item, dict) for item in recommendations):
            raise OpenRouterResponseError("OpenRouter recommendation response must be a JSON array of objects", RecommendationErrorCategory.INVALID_JSON)
        return recommendations

    def _request_with_retries(self, client: httpx.Client, headers: dict[str, str], payload: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            try:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if response.status_code in {401, 403}:
                    raise OpenRouterAuthenticationError(
                        f"OpenRouter authentication failed (HTTP {response.status_code}). "
                        "Check the configured API key and endpoint profile."
                    )
                if response.status_code == 402:
                    raise OpenRouterResponseError("OpenRouter reported insufficient credits", RecommendationErrorCategory.INSUFFICIENT_CREDITS)
                if response.status_code == 404:
                    raise OpenRouterResponseError("OpenRouter model or endpoint was unavailable", RecommendationErrorCategory.MODEL_UNAVAILABLE)
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 4))
                        continue
                    raise OpenRouterResponseError("OpenRouter rate limit reached", RecommendationErrorCategory.RATE_LIMIT)
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 4))
                        continue
                    raise OpenRouterResponseError("OpenRouter provider returned a server error", RecommendationErrorCategory.PROVIDER_ERROR)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                raise OpenRouterResponseError(f"OpenRouter request failed after retries: {type(exc).__name__}", RecommendationErrorCategory.NETWORK_ERROR) from exc
            except httpx.HTTPStatusError as exc:
                raise OpenRouterResponseError(f"OpenRouter returned HTTP {exc.response.status_code}", RecommendationErrorCategory.PROVIDER_ERROR) from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise OpenRouterResponseError("OpenRouter returned an unusable response") from exc
        raise OpenRouterResponseError("OpenRouter request failed after retries")

