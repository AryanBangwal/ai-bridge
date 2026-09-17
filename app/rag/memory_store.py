"""Thread-safe, process-local keyword retrieval with cosine similarity."""

import math
import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

from app.rag.base import BaseVectorStore


def _tokens(text: str) -> Counter:
    return Counter(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


@dataclass(frozen=True)
class _Document:
    id: str
    text: str
    metadata: dict
    terms: Counter
    norm: float


class InMemoryVectorStore(BaseVectorStore):
    """No persistence, external services, stemming, or semantic embeddings.

    Each supplied string is one chunk. Equal scores retain ingestion order;
    zero-overlap documents are excluded. Metadata is retained but not searched.
    """

    def __init__(self) -> None:
        self._documents: list[_Document] = []
        self._lock = RLock()

    def add_documents(
        self, documents: list[str], metadatas: list[dict] | None = None
    ) -> list[str]:
        if not isinstance(documents, list) or any(
            not isinstance(text, str) or not text.strip() for text in documents
        ):
            raise ValueError("Documents must be a list of nonblank strings")
        if metadatas is not None and (
            not isinstance(metadatas, list)
            or len(metadatas) != len(documents)
            or any(not isinstance(metadata, dict) for metadata in metadatas)
        ):
            raise ValueError("Metadata must contain one dictionary per document")
        # Prepare the entire batch before mutation so failed ingestion is atomic.
        batch = []
        for index, text in enumerate(documents):
            terms = _tokens(text)
            batch.append(
                _Document(
                    id=str(uuid4()),
                    text=text.strip(),
                    metadata=deepcopy(metadatas[index])
                    if metadatas is not None
                    else {},
                    terms=terms,
                    norm=math.sqrt(sum(count * count for count in terms.values())),
                )
            )
        with self._lock:
            self._documents.extend(batch)
        return [document.id for document in batch]

    def similarity_search(self, query: str, k: int = 3) -> list[str]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a nonblank string")
        if type(k) is not int or k < 1:
            raise ValueError("k must be a positive integer")
        terms = _tokens(query)
        norm = math.sqrt(sum(count * count for count in terms.values()))
        if not norm:
            return []
        with self._lock:
            documents = tuple(self._documents)
        scores = []
        for document in documents:
            overlap = sum(
                count * document.terms.get(term, 0) for term, count in terms.items()
            )
            if overlap:
                scores.append((overlap / (norm * document.norm), document.text))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in scores[:k]]
