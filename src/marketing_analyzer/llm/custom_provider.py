"""Custom OpenAI-compatible endpoint adapter."""

from .openrouter_provider import OpenRouterProvider


class CustomOpenAICompatibleProvider(OpenRouterProvider):
    """Use an explicitly configured custom OpenAI-compatible endpoint."""

