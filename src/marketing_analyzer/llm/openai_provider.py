"""OpenAI-compatible direct provider adapter."""

from .openrouter_provider import OpenRouterProvider


class OpenAIProvider(OpenRouterProvider):
    """Use the OpenAI Chat Completions protocol at a configurable base URL."""

