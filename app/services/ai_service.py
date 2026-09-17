"""
app/services/ai_service.py

AIService is the main orchestration layer between the application and the
selected AI provider.

Data flow:
    Application
        ↓
    AIService.generate()
        ↓
    BaseProvider.generate()   ← provider abstraction
        ↓
    OllamaProvider (or any other concrete provider)
        ↓
    Ollama / other model

AIService depends only on BaseProvider, not on any specific provider.
This means the provider can be swapped without touching this file.
"""

from app.providers.base import BaseProvider
from app.providers.errors import InvalidProviderResponseError


class AIService:
    """
    Orchestrates AI requests through a configurable provider.

    The provider is injected at construction time, keeping AIService
    decoupled from any particular model or service.
    """

    def __init__(self, provider: BaseProvider) -> None:
        # Store whichever provider was supplied — Ollama, OpenAI, etc.
        self.provider = provider

    def generate(self, prompt: str) -> str:
        """
        Process a prompt and return the AI-generated response.

        This is the single entry point the application should call.
        Any future pre-processing (prompt formatting, context injection,
        RAG retrieval) or post-processing (response parsing, filtering)
        will be added here without changing the method signature.

        Args:
            prompt: The input text from the application.

        Returns:
            The AI-generated response string.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")
        # Future: add prompt enrichment, RAG context, tool selection here
        response = self.provider.generate(prompt)
        if not isinstance(response, str) or not response.strip():
            raise InvalidProviderResponseError("AI provider returned no valid response text")
        return response

    def __repr__(self) -> str:
        return f"<AIService provider={self.provider!r}>"
