"""Named endpoint profiles and provider construction."""

from dataclasses import dataclass
import os

from .base_provider import LLMProvider
from .openrouter_provider import OpenRouterProvider


@dataclass(frozen=True)
class EndpointProfile:
    name: str
    provider: str
    base_url: str
    api_key_env: str
    model_env: str
    default_model: str


class EndpointRegistry:
    def __init__(self, profiles: dict[str, EndpointProfile] | None = None) -> None:
        self._profiles = profiles or default_endpoint_profiles()

    def register(self, profile: EndpointProfile) -> None:
        self._profiles[profile.name] = profile

    def get(self, name: str) -> EndpointProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._profiles))
            raise ValueError(f"Unknown LLM endpoint profile '{name}'. Available profiles: {known}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._profiles))


def default_endpoint_profiles() -> dict[str, EndpointProfile]:
    return {
        "openrouter_default": EndpointProfile(
            "openrouter_default", "openrouter", os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openrouter/auto",
        ),
        "openai_direct": EndpointProfile(
            "openai_direct", "openai", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini",
        ),
        "gemini_direct": EndpointProfile(
            "gemini_direct", "gemini", "https://generativelanguage.googleapis.com/v1beta",
            "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash",
        ),
        "custom_openai_compatible": EndpointProfile(
            "custom_openai_compatible", "custom", os.getenv("CUSTOM_LLM_BASE_URL", ""),
            "CUSTOM_LLM_API_KEY", "CUSTOM_LLM_MODEL", "",
        ),
    }


def create_provider(profile: EndpointProfile, model: str | None = None) -> LLMProvider:
    selected_model = model or os.getenv(profile.model_env) or profile.default_model
    api_key = os.getenv(profile.api_key_env)
    if profile.provider in {"openrouter", "openai", "custom"}:
        if not profile.base_url:
            raise ValueError(f"Base URL is required for endpoint profile '{profile.name}'")
        provider_type = OpenRouterProvider
        if profile.provider == "openai":
            from .openai_provider import OpenAIProvider

            provider_type = OpenAIProvider
        elif profile.provider == "custom":
            from .custom_provider import CustomOpenAICompatibleProvider

            provider_type = CustomOpenAICompatibleProvider
        return provider_type(
            api_key=api_key,
            model=selected_model,
            base_url=profile.base_url,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        )
    if profile.provider == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=selected_model, base_url=profile.base_url, timeout_seconds=float(os.getenv("LLM_TIMEOUT", "60")), max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")))
    raise ValueError(f"Unsupported LLM provider: {profile.provider}")

