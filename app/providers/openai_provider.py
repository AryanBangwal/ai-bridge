"""HTTP adapter for the OpenAI-compatible chat-completions protocol."""
import httpx

from app.config import settings
from app.providers.base import BaseProvider
from app.providers.errors import (
    InvalidProviderResponseError,
    ProviderAuthorizationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OpenAIProvider(BaseProvider):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        try:
            self.base_url = settings.normalize_base_url(base_url, "OPENAI_BASE_URL")
            self.model = settings.validate_text(model, "OPENAI_MODEL")
            self._api_key = settings.validate_text(api_key, "OPENAI_API_KEY")
            if not self._api_key.isascii() or any(c.isspace() for c in self._api_key):
                raise ValueError("Invalid API key")
        except ValueError as exc:
            raise ProviderConfigurationError("OpenAI-compatible provider configuration is invalid") from exc
        # Accept both a server root and the customary versioned base URL.
        api_base = self.base_url if self.base_url.endswith("/v1") else self.base_url + "/v1"
        self._endpoint = api_base + "/chat/completions"

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")
        try:
            response = httpx.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=httpx.Timeout(120.0, connect=5.0),
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("AI provider timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError("AI provider is unreachable") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise ProviderAuthorizationError("AI provider rejected server credentials") from exc
            if exc.response.status_code in {429, 503}:
                raise ProviderUnavailableError("AI provider is temporarily unavailable") from exc
            raise ProviderError("AI provider rejected the generation request") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidProviderResponseError("AI provider returned invalid JSON") from exc
        if not isinstance(data, dict) or "error" in data:
            raise InvalidProviderResponseError("AI provider returned an invalid payload")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise InvalidProviderResponseError("AI provider returned no valid choices")
        message = choices[0].get("message")
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise InvalidProviderResponseError("AI provider returned no valid response text")
        return text
