"""Provider construction registry; register custom builders at application setup."""
from collections.abc import Callable
from typing import ClassVar

from app.config import settings
from app.providers.base import BaseProvider
from app.providers.errors import InvalidProviderError, ProviderConfigurationError
from app.providers.ollama import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


def _ollama(model: str | None) -> BaseProvider:
    return OllamaProvider(model=model)


def _openai(model: str | None) -> BaseProvider:
    return OpenAIProvider(
        base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL if model is None else model,
    )


class ProviderFactory:
    registry: ClassVar[dict[str, Callable[[str | None], BaseProvider]]] = {
        "ollama": _ollama,
        "openai": _openai,
    }

    @classmethod
    def get_provider(cls, provider_name: str | None = None, model_name: str | None = None) -> BaseProvider:
        name = settings.DEFAULT_PROVIDER if provider_name is None else provider_name
        if not isinstance(name, str) or name.strip().lower() not in cls.registry:
            if provider_name is None:
                raise ProviderConfigurationError("Default AI provider is not registered")
            raise InvalidProviderError("Unknown AI provider")
        name = name.strip().lower()
        try:
            if model_name is not None:
                model_name = settings.validate_text(model_name, "model")
            return cls.registry[name](model_name)
        except ValueError as exc:
            raise ProviderConfigurationError("AI provider configuration is invalid") from exc
