"""Offline retrieval, augmentation, and endpoint tests."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app, get_vector_store
from app.providers.base import BaseProvider
from app.providers.errors import ProviderUnavailableError
from app.rag.base import BaseVectorStore
from app.rag.memory_store import InMemoryVectorStore
from app.services.ai_service import AIService
from app.services.rag_service import RAGService


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryVectorStore()

    def test_ingestion_ids_and_ranking(self):
        ids = self.store.add_documents(
            ["apple banana", "apple", "orange"], [{"source": "a"}, {}, {}]
        )
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(
            self.store.similarity_search("APPLE!", 2), ["apple", "apple banana"]
        )
        self.assertEqual(self.store.similarity_search("orange", 20), ["orange"])
        self.assertEqual(self.store.similarity_search("missing"), [])
        self.assertEqual(self.store.similarity_search("!!!"), [])

    def test_empty_store_and_empty_batch(self):
        self.assertEqual(self.store.add_documents([]), [])
        self.assertEqual(self.store.similarity_search("hello"), [])

    def test_atomic_validation(self):
        for docs, metadata in (
            (["valid", " "], None),
            (["valid"], []),
            (["valid"], [None]),
            ("text", None),
        ):
            with self.subTest(docs=docs), self.assertRaises(ValueError):
                self.store.add_documents(docs, metadata)
        self.assertEqual(self.store.similarity_search("valid"), [])
        for query, k in (
            ("", 3),
            (None, 3),
            ("query", 0),
            ("query", True),
            ("query", 1.5),
        ):
            with self.assertRaises(ValueError):
                self.store.similarity_search(query, k)

    def test_ties_unicode_and_metadata_copy(self):
        metadata = [{"nested": {"value": 1}}]
        self.store.add_documents(["caf? alpha"], metadata)
        metadata[0]["nested"]["value"] = 2
        self.assertEqual(self.store._documents[0].metadata["nested"]["value"], 1)
        self.store.add_documents(["caf? beta"])
        self.assertEqual(
            self.store.similarity_search("CAF?"), ["caf? alpha", "caf? beta"]
        )

    def test_concurrent_ingestion_and_search(self):
        def ingest(index):
            ids = self.store.add_documents([f"shared document {index}"])
            self.store.similarity_search("shared")
            return ids[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(ingest, range(40)))
        self.assertEqual(len(set(ids)), 40)
        self.assertEqual(len(self.store.similarity_search("shared", k=100)), 40)


class RAGServiceTests(unittest.TestCase):
    def setUp(self):
        self.provider = Mock(spec=BaseProvider)
        self.provider.generate.return_value = "answer"
        self.store = Mock(spec=BaseVectorStore)
        self.store.similarity_search.return_value = ["first chunk", "second chunk"]
        self.service = RAGService(AIService(self.provider), self.store)

    def test_retrieved_prompt(self):
        self.assertEqual(self.service.generate("question", use_rag=True, k=2), "answer")
        self.store.similarity_search.assert_called_once_with("question", k=2)
        self.provider.generate.assert_called_once_with(
            "Context:\nfirst chunk\n\nsecond chunk\n\nQuestion: question"
        )

    def test_explicit_only_skips_retrieval(self):
        self.service.generate("question", explicit_context=" supplied ")
        self.store.similarity_search.assert_not_called()
        self.provider.generate.assert_called_once_with(
            "Context:\nsupplied\n\nQuestion: question"
        )

    def test_combined_context_and_budget(self):
        self.service.generate(
            "question", explicit_context="supplied", use_rag=True, max_context_chars=15
        )
        self.provider.generate.assert_called_once_with(
            "Context:\nsupplied\n\nfirst\n\nQuestion: question"
        )

    def test_no_context_preserves_query(self):
        self.store.similarity_search.return_value = []
        self.service.generate("question", use_rag=True)
        self.provider.generate.assert_called_once_with("question")

    def test_direct_input_validation(self):
        for kwargs in (
            {"query": " "},
            {"query": "q", "k": 0},
            {"query": "q", "max_context_chars": 0},
            {"query": "q", "explicit_context": 3},
            {"query": "q", "use_rag": "yes"},
        ):
            with self.assertRaises(ValueError):
                self.service.generate(**kwargs)
        self.provider.generate.assert_not_called()


class RAGAPITests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryVectorStore()
        app.dependency_overrides[get_vector_store] = lambda: self.store
        self.addCleanup(app.dependency_overrides.clear)
        self.provider = Mock(spec=BaseProvider)
        self.provider.generate.return_value = "answer"
        patcher = patch(
            "app.main.ProviderFactory.get_provider", return_value=self.provider
        )
        self.factory = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def test_ingest_then_retrieve_and_route(self):
        result = self.client.post(
            "/api/v1/rag/ingest",
            json={
                "documents": ["Python is a language", "Bananas are fruit"],
                "metadatas": [{"source": "manual"}, {}],
            },
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["count"], 2)
        self.assertEqual(len(set(result.json()["ids"])), 2)
        self.factory.assert_not_called()
        result = self.client.post(
            "/api/v1/generate-with-context",
            json={
                "query": "Python",
                "use_rag": True,
                "k": 1,
                "provider": "openai",
                "model": "chosen",
            },
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"response": "answer"})
        self.factory.assert_called_once_with("openai", "chosen")
        self.provider.generate.assert_called_once_with(
            "Context:\nPython is a language\n\nQuestion: Python"
        )

    def test_explicit_and_default_query(self):
        for extra, expected in (
            ({}, "question"),
            (
                {"explicit_context": "supplied"},
                "Context:\nsupplied\n\nQuestion: question",
            ),
        ):
            result = self.client.post(
                "/api/v1/generate-with-context", json={"query": "question", **extra}
            )
            self.assertEqual(result.status_code, 200)
            self.provider.generate.assert_called_with(expected)

    def test_invalid_ingestion_does_not_mutate(self):
        for body in (
            {"documents": []},
            {"documents": ["valid", " "]},
            {"documents": ["valid"], "metadatas": []},
            {"documents": ["valid"], "metadatas": [3]},
            {"documents": ["a"] * 101},
        ):
            self.assertEqual(
                self.client.post("/api/v1/rag/ingest", json=body).status_code, 422
            )
        self.assertEqual(self.store.similarity_search("valid"), [])

    def test_query_limits(self):
        for extra in (
            {"query": ""},
            {"k": 0},
            {"k": 21},
            {"k": True},
            {"use_rag": "true"},
            {"max_context_chars": 0},
            {"max_context_chars": 64001},
            {"explicit_context": 42},
            {"unknown": 1},
        ):
            result = self.client.post(
                "/api/v1/generate-with-context", json={"query": "hello", **extra}
            )
            self.assertEqual(result.status_code, 422, result.text)
        self.provider.generate.assert_not_called()

    def test_provider_error_propagates(self):
        self.provider.generate.side_effect = ProviderUnavailableError(
            "AI provider is unreachable"
        )
        result = self.client.post(
            "/api/v1/generate-with-context", json={"query": "hello"}
        )
        self.assertEqual(result.status_code, 503)

    def test_store_is_shared_across_requests_without_override(self):
        app.dependency_overrides.pop(get_vector_store)
        with patch.object(app.state, "vector_store", InMemoryVectorStore()):
            self.client.post("/api/v1/rag/ingest", json={"documents": ["shared fact"]})
            self.client.post(
                "/api/v1/generate-with-context",
                json={"query": "shared", "use_rag": True},
            )
            self.provider.generate.assert_called_with(
                "Context:\nshared fact\n\nQuestion: shared"
            )

    def test_openapi_new_endpoints(self):
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/api/v1/generate-with-context"]["post"]
        self.assertEqual(
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ContextQueryRequest",
        )
        self.assertIn("201", schema["paths"]["/api/v1/rag/ingest"]["post"]["responses"])
