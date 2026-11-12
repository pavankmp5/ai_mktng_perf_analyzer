"""LLM boundary; concrete providers can be added without changing analysis."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_recommendations(self, context: dict) -> list[dict]:
        """Turn a bounded analysis context into unvalidated recommendation dictionaries."""
        raise NotImplementedError

