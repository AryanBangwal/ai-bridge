"""Offline factory, adapter, and dynamic routing regressions."""
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.providers.base import BaseProvider
from app.providers.errors import (
    InvalidProviderError,
    InvalidProviderResponseError,
    ProviderAuthorizationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.factory import ProviderFactory
from app.providers.ollama import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


def reply(status=200, **kwargs):
    return httpx.Response(status, request=httpx.Request("POST", "https://backend/v1/chat/completions"), **kwargs)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        for name, value in {"DEFAULT_PROVIDER": "ollama", "DEFAULT_MODEL": "local-default",
                            "OPENAI_BASE_URL": "https://backend/v1/", "OPENAI_API_KEY": "test-secret",
                            "OPENAI_MODEL": "remote-default"}.items():
            patcher = patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def test_factory_defaults_and_overrides(self):
        for name in (None, "ollama", " OLLAMA "):
            provider = ProviderFactory.get_provider(name)
            self.assertIsInstance(provider, OllamaProvider)
            self.assertEqual(provider.model, "local-default")
        remote = ProviderFactory.get_provider("openai")
        self.assertIsInstance(remote, OpenAIProvider)
        self.assertEqual(remote.model, "remote-default")
        for name in ("ollama", "openai"):
            self.assertEqual(ProviderFactory.get_provider(name, "override").model, "override")
        with patch.object(settings, "DEFAULT_PROVIDER", "openai"):
            self.assertIsInstance(ProviderFactory.get_provider(), OpenAIProvider)
        self.assertEqual(ProviderFactory.get_provider("ollama").model, "local-default")

    def test_unknown_provider_and_bad_default(self):
        for name in ("unknown", "", " "):
            with self.assertRaises(InvalidProviderError):
                ProviderFactory.get_provider(name)
        with patch.object(settings, "DEFAULT_PROVIDER", "unknown"), self.assertRaises(ProviderConfigurationError):
            ProviderFactory.get_provider()

    def test_custom_registry_builder(self):
        class CustomProvider(BaseProvider):
            def generate(self, prompt):
                return "custom: " + prompt
        with patch.dict(ProviderFactory.registry, {"custom": lambda model: CustomProvider()}):
            self.assertIsInstance(ProviderFactory.get_provider("custom"), CustomProvider)
            result = self.client.post("/api/v1/generate", json={"prompt": "hi", "provider": "custom"})
            self.assertEqual(result.json(), {"response": "custom: hi"})

    def test_chat_payload_auth_and_url(self):
        for base in ("https://backend", "https://backend/", "https://backend/v1///"):
            provider = OpenAIProvider(base, "test-secret", "chosen")
            with patch("app.providers.openai_provider.httpx.post", return_value=reply(json={"choices": [{"message": {"content": "answer"}}]})) as post:
                self.assertEqual(provider.generate("hello"), "answer")
                self.assertEqual(post.call_args.args[0], "https://backend/v1/chat/completions")
                self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer test-secret"})
                self.assertEqual(post.call_args.kwargs["json"], {"model": "chosen", "messages": [{"role": "user", "content": "hello"}], "stream": False})
            self.assertNotIn("test-secret", repr(provider))

    def test_explicit_error_types(self):
        provider = ProviderFactory.get_provider("openai")
        for code, kind in ((401, ProviderAuthorizationError), (403, ProviderAuthorizationError),
                           (429, ProviderUnavailableError), (503, ProviderUnavailableError), (500, ProviderError)):
            with self.subTest(code=code), patch("httpx.post", return_value=reply(code, text="sensitive upstream body")):
                with self.assertRaises(kind) as error:
                    provider.generate("hi")
                self.assertNotIn("sensitive", str(error.exception))
        for exc, kind in ((httpx.ConnectError("secret"), ProviderUnavailableError), (httpx.ReadTimeout("secret"), ProviderTimeoutError)):
            with patch("httpx.post", side_effect=exc), self.assertRaises(kind):
                provider.generate("hi")

    def test_malformed_chat_responses(self):
        provider = ProviderFactory.get_provider("openai")
        for payload in (None, [], {}, {"error": "private"}, {"choices": []}, {"choices": {}},
                        {"choices": [None]}, {"choices": [{}]}, {"choices": [{"message": None}]},
                        *({"choices": [{"message": {"content": text}}]} for text in (None, "", " ", 3, []))):
            with self.subTest(payload=payload), patch("httpx.post", return_value=reply(json=payload)), self.assertRaises(InvalidProviderResponseError):
                provider.generate("hi")
        with patch("httpx.post", return_value=reply(text="invalid JSON")), self.assertRaises(InvalidProviderResponseError):
            provider.generate("hi")

    def test_optional_backend_configuration(self):
        with patch.object(settings, "OPENAI_API_KEY", ""):
            self.assertIsInstance(ProviderFactory.get_provider(), OllamaProvider)
            with self.assertRaises(ProviderConfigurationError):
                ProviderFactory.get_provider("openai")
            with patch("httpx.post") as post:
                self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "hi", "provider": "openai"}).status_code, 503)
                post.assert_not_called()
        with patch.object(settings, "OPENAI_MODEL", ""):
            self.assertEqual(ProviderFactory.get_provider("openai", "explicit").model, "explicit")

    def test_routing_preserves_contract_and_model_isolation(self):
        def respond(url, **kwargs):
            if url.endswith("/chat/completions"):
                return reply(json={"choices": [{"message": {"content": kwargs["json"]["model"]}}]})
            return reply(json={"response": kwargs["json"]["model"]})
        with patch("httpx.post", side_effect=respond):
            for extra, expected in (({}, "local-default"), ({"provider": None, "model": None}, "local-default"),
                                    ({"model": "local-custom"}, "local-custom"),
                                    ({"provider": "openai"}, "remote-default"),
                                    ({"provider": "openai", "model": "remote-custom"}, "remote-custom"),
                                    ({}, "local-default")):
                result = self.client.post("/api/v1/generate", json={"prompt": "hi", **extra})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json(), {"response": expected})

    def test_selection_errors_and_http_mappings(self):
        with patch("httpx.post") as post:
            self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "hi", "provider": "unknown"}).status_code, 400)
            for field in ("provider", "model"):
                for value in ("", " ", 4, []):
                    self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "hi", field: value}).status_code, 422)
            post.assert_not_called()
        for code, expected in ((401, 502), (403, 502), (429, 503)):
            with patch("httpx.post", return_value=reply(code, text="test-secret")):
                result = self.client.post("/api/v1/generate", json={"prompt": "hi", "provider": "openai"})
                self.assertEqual(result.status_code, expected)
                self.assertNotIn("test-secret", result.text)

    def test_health_uses_default_provider_without_network(self):
        with patch.object(settings, "DEFAULT_PROVIDER", "openai"), patch("httpx.post") as post:
            result = self.client.get("/health")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["provider"], "openai")
            self.assertEqual(result.json()["model"], "remote-default")
            post.assert_not_called()
