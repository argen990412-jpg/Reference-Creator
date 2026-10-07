from __future__ import annotations

from .base import ImageProvider, ProviderError

PROVIDERS = ("gemini", "openai", "mock")


def get_provider(name: str, **kwargs) -> ImageProvider:
    name = name.lower()
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(**kwargs)
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(**kwargs)
    if name == "mock":
        from .mock import MockProvider
        return MockProvider()
    raise ProviderError(f"Unknown provider '{name}'. Choose from: {', '.join(PROVIDERS)}")


__all__ = ["ImageProvider", "ProviderError", "get_provider", "PROVIDERS"]
