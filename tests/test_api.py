"""Offline regression tests for the HTTP API and provider boundary."""
import unittest
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient

from app.config.settings import normalize_base_url
from app.main import app, get_ai_service
from app.providers.base import BaseProvider
from app.providers.errors import InvalidProviderResponseError
from app.providers.ollama import OllamaProvider
from app.services.ai_service import AIService


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)

    def upstream(self, status=200, **kwargs):
        return httpx.Response(status, request=httpx.Request("POST", "http://ollama/api/generate"), **kwargs)

    def test_health_does_not_call_provider(self):
        with patch("app.providers.ollama.httpx.post") as post:
            result = self.client.get("/health")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["configuration"], "valid")
        post.assert_not_called()

    def test_generation_and_url_normalization(self):
        app.dependency_overrides[get_ai_service] = lambda: AIService(OllamaProvider("http://localhost:11434///"))
        with patch("app.providers.ollama.httpx.post", return_value=self.upstream(json={"response": "Hello"})) as post:
            result = self.client.post("/api/v1/generate", json={"prompt": " Hi "})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"response": "Hello"})
        self.assertEqual(post.call_args.args[0], "http://localhost:11434/api/generate")
        self.assertEqual(post.call_args.kwargs["json"]["prompt"], "Hi")
        self.assertIs(post.call_args.kwargs["json"]["stream"], False)

    def test_invalid_requests(self):
        for body in ({}, {"prompt": ""}, {"prompt": "  "}, {"prompt": None},
                     {"prompt": 5}, {"prompt": "x" * 32001}, {"prompt": "hi", "unexpected": "other"}):
            with self.subTest(body=str(body)[:80]), patch("app.providers.ollama.httpx.post") as post:
                self.assertEqual(self.client.post("/api/v1/generate", json=body).status_code, 422)
                post.assert_not_called()

    def test_transport_errors(self):
        for exc, status in ((httpx.ConnectError("private host"), 503),
                            (httpx.ReadTimeout("private host"), 504),
                            (httpx.ConnectTimeout("private host"), 504)):
            with self.subTest(error=type(exc)), patch("app.providers.ollama.httpx.post", side_effect=exc):
                result = self.client.post("/api/v1/generate", json={"prompt": "Hi"})
                self.assertEqual(result.status_code, status)
                self.assertNotIn("private host", result.text)

    def test_upstream_status_errors(self):
        for upstream_status, expected in ((404, 502), (500, 502), (429, 503), (503, 503)):
            with self.subTest(status=upstream_status), patch("app.providers.ollama.httpx.post", return_value=self.upstream(upstream_status, text="private error")):
                result = self.client.post("/api/v1/generate", json={"prompt": "Hi"})
                self.assertEqual(result.status_code, expected)
                self.assertNotIn("private error", result.text)

    def test_invalid_upstream_payloads(self):
        for payload in ({}, {"response": None}, {"response": 3}, {"response": ""},
                        {"response": "  "}, [], {"error": "private", "response": "text"}):
            with self.subTest(payload=payload), patch("app.providers.ollama.httpx.post", return_value=self.upstream(json=payload)):
                self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "Hi"}).status_code, 502)
        with patch("app.providers.ollama.httpx.post", return_value=self.upstream(text="not JSON")):
            self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "Hi"}).status_code, 502)

    def test_unexpected_error_is_sanitized(self):
        with patch("app.providers.ollama.httpx.post", side_effect=RuntimeError("secret")), self.assertLogs("app.main", level="ERROR"):
            result = self.client.post("/api/v1/generate", json={"prompt": "Hi"})
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.json(), {"detail": "Internal server error"})

    def test_provider_can_be_replaced(self):
        class AlternativeProvider(BaseProvider):
            def generate(self, prompt: str) -> str:
                return "Alternative: " + prompt
        app.dependency_overrides[get_ai_service] = lambda: AIService(AlternativeProvider())
        self.assertEqual(self.client.post("/api/v1/generate", json={"prompt": "Hi"}).json(), {"response": "Alternative: Hi"})

    def test_service_validation(self):
        provider = Mock(spec=BaseProvider)
        service = AIService(provider)
        for prompt in (None, "", "  ", 3):
            with self.assertRaises(ValueError):
                service.generate(prompt)
        provider.generate.assert_not_called()
        for response in (None, "", "  ", 3):
            provider.generate.return_value = response
            with self.assertRaises(InvalidProviderResponseError):
                service.generate("Hi")

    def test_configuration_validation(self):
        self.assertEqual(normalize_base_url(" https://example.com/prefix/// "), "https://example.com/prefix")
        for value in ("", " ", "localhost:11434", "ftp://localhost", "http://", "http://host:bad", "http://host:0", "http://host?x=1", "http://host#fragment", "http://user:password@host"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_base_url(value)
        with self.assertRaises(ValueError):
            OllamaProvider(model=" ")

    def test_openapi_contract(self):
        schema = self.client.get("/openapi.json").json()
        responses = schema["paths"]["/api/v1/generate"]["post"]["responses"]
        self.assertTrue({"200", "422", "500", "502", "503", "504"}.issubset(responses))


if __name__ == "__main__":
    unittest.main()
