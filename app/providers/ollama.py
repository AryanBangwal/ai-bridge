"""
app/providers/ollama.py

Ollama implementation of BaseProvider.

Communicates with the Ollama HTTP API using the httpx library.
Configuration is read from environment variables via app/config/settings.py.

Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import httpx

from app.providers.base import BaseProvider
from app.config import settings


class OllamaProvider(BaseProvider):
    """
    Sends prompts to a locally running Ollama instance via its REST API.

    Ollama must be installed and running for requests to succeed.
    If Ollama is not available, a clear error message is returned rather
    than raising an unhandled exception — this keeps the application
    stable during development when the model may not be running.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        # Allow callers to override settings; fall back to environment config.
        self.base_url: str = base_url or settings.OLLAMA_BASE_URL
        self.model: str = model or settings.DEFAULT_MODEL

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the generated text.

        Uses the /api/generate endpoint with stream=False so the full
        response is returned in a single HTTP reply.

        Args:
            prompt: The input text to send to the model.

        Returns:
            The model's response text, or an error message string.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Return full response, not a stream
        }

        try:
            # Use a generous timeout — local models can be slow to respond
            response = httpx.post(url, json=payload, timeout=120.0)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

        except httpx.ConnectError:
            return (
                f"[OllamaProvider] Could not connect to Ollama at {self.base_url}. "
                "Is Ollama running? Try: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            return f"[OllamaProvider] HTTP error from Ollama: {e.response.status_code} — {e.response.text}"
        except Exception as e:
            return f"[OllamaProvider] Unexpected error: {e}"

    def __repr__(self) -> str:
        return f"<OllamaProvider model={self.model!r} base_url={self.base_url!r}>"
