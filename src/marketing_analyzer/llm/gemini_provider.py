"""Gemini REST adapter using the official generateContent endpoint."""

from __future__ import annotations

import json
import os
import time

import httpx

from .openrouter_provider import OpenRouterConfigurationError, OpenRouterResponseError
from .base_provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str = "https://generativelanguage.googleapis.com/v1beta", timeout_seconds: float = 60.0, max_retries: int = 2, client: httpx.Client | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client

    def generate_recommendations(self, context: dict) -> list[dict]:
        if not self.api_key:
            raise OpenRouterConfigurationError("GEMINI_API_KEY is not configured")
        prompt = (
            "You are a marketing performance analyst. Return only a JSON array matching the requested "
            "recommendation schema. Use only supplied facts and do not invent metrics or trends.\n\n"
            + json.dumps(context, ensure_ascii=False)
        )
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        close = self.client is None
        try:
            body = self._request_with_retries(client, headers, payload)
        finally:
            if close:
                client.close()
        try:
            content = body["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise OpenRouterResponseError("Gemini returned invalid recommendation JSON") from exc
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise OpenRouterResponseError("Gemini recommendation response must be a JSON array of objects")
        return result

    def _request_with_retries(self, client: httpx.Client, headers: dict[str, str], payload: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            try:
                response = client.post(f"{self.base_url}/models/{self.model}:generateContent", headers=headers, json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 4))
                        continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                raise OpenRouterResponseError(f"Gemini request failed after retries: {type(exc).__name__}") from exc
            except httpx.HTTPStatusError as exc:
                raise OpenRouterResponseError(f"Gemini returned HTTP {exc.response.status_code}") from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise OpenRouterResponseError("Gemini returned an unusable response") from exc
        raise OpenRouterResponseError("Gemini request failed after retries")
