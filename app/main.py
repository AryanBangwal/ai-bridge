"""
app/main.py

Entry point for AI Bridge.

Demonstrates that the provider abstraction and service layer initialise
correctly.  Running this file verifies the architecture is wired up
before any API layer is introduced.

Usage:
    python -m app.main
    # or from the project root:
    python app/main.py
"""

from app.config import settings
from app.providers.ollama import OllamaProvider
from app.services.ai_service import AIService


def main() -> None:
    print("=" * 50)
    print("  AI Bridge — starting up")
    print("=" * 50)
    print(f"  Environment : {settings.APP_ENV}")
    print(f"  Provider    : Ollama")
    print(f"  Ollama URL  : {settings.OLLAMA_BASE_URL}")
    print(f"  Model       : {settings.DEFAULT_MODEL}")
    print("=" * 50)

    # Wire up the provider and inject it into the service.
    # To switch providers later, only this wiring changes — AIService stays untouched.
    provider = OllamaProvider()
    service = AIService(provider=provider)

    print(f"\nInitialised: {service}\n")

    # Send a simple test prompt to verify the full chain is reachable.
    prompt = "Reply with a single sentence confirming you are working."
    print(f"Sending test prompt: {prompt!r}\n")

    response = service.generate(prompt)
    print(f"Response:\n  {response}\n")


if __name__ == "__main__":
    main()
