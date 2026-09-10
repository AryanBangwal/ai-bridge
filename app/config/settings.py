"""
app/config/settings.py

Reads configuration from environment variables.
Values can be overridden by creating a .env file (see .env.example).
"""

import os
from dotenv import load_dotenv

# Load .env file if it exists. Does nothing if the file is absent.
load_dotenv()


# --- Application ---

# Application environment: "development" or "production"
APP_ENV: str = os.getenv("APP_ENV", "development")


# --- Ollama provider ---

# Base URL for the Ollama API
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Default model name to request from Ollama
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama3.2")
