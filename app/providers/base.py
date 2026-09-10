"""
app/providers/base.py

Defines the abstract interface that every AI provider must implement.

Any provider (Ollama, OpenAI, a custom model, etc.) must subclass
BaseProvider and implement its methods.  The rest of the application
should only ever interact with this interface — never with a concrete
provider class directly.

This keeps the application decoupled from any specific model or service.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    Abstract base class for AI model providers.

    To add a new provider (e.g. OpenAI, Anthropic, a custom model):
    1. Create a new file in app/providers/
    2. Subclass BaseProvider
    3. Implement the generate() method
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the model and return the generated text response.

        Args:
            prompt: The input text to send to the model.

        Returns:
            The model's text response as a string.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
