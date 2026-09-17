"""Environment configuration validated at startup."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def validate_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def normalize_base_url(value: str, name: str = "OLLAMA_BASE_URL") -> str:
    value = validate_text(value, name).rstrip("/")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid = (parsed.scheme in {"http", "https"} and parsed.hostname
                 and parsed.username is None and parsed.password is None
                 and not parsed.query and not parsed.fragment
                 and not any(c.isspace() for c in value)
                 and (port is None or port > 0))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be an HTTP(S) URL without credentials, query, or fragment")
    return value


APP_ENV = validate_text(os.getenv("APP_ENV", "development"), "APP_ENV")
if APP_ENV not in {"development", "production"}:
    raise ValueError("APP_ENV must be development or production")
OLLAMA_BASE_URL = normalize_base_url(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
DEFAULT_MODEL = validate_text(os.getenv("DEFAULT_MODEL", "llama3.2"), "DEFAULT_MODEL")

# OpenAI-compatible configuration is validated only when selected.
DEFAULT_PROVIDER = validate_text(os.getenv("DEFAULT_PROVIDER", "ollama"), "DEFAULT_PROVIDER").lower()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
