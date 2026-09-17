"""Synchronous Ollama adapter; failures propagate as typed exceptions."""
import httpx

from app.config import settings
from app.providers.base import BaseProvider
from app.providers.errors import (
    InvalidProviderResponseError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = settings.normalize_base_url(
            settings.OLLAMA_BASE_URL if base_url is None else base_url
        )
        self.model = settings.validate_text(
            settings.DEFAULT_MODEL if model is None else model, "model"
        )

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=httpx.Timeout(120.0, connect=5.0),
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("AI provider timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("AI provider is unreachable") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 503}:
                raise ProviderUnavailableError("AI provider is temporarily unavailable") from exc
            raise ProviderError("AI provider rejected the generation request") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidProviderResponseError("AI provider returned invalid JSON") from exc
        if not isinstance(data, dict) or "error" in data:
            raise InvalidProviderResponseError("AI provider returned an invalid payload")
        text = data.get("response")
        if not isinstance(text, str) or not text.strip():
            raise InvalidProviderResponseError("AI provider returned no valid response text")
        return text

    def __repr__(self) -> str:
        return f"<OllamaProvider model={self.model!r} base_url={self.base_url!r}>"
