"""Storage contract for retrieval, independent of providers and HTTP."""

from abc import ABC, abstractmethod


class BaseVectorStore(ABC):
    @abstractmethod
    def add_documents(
        self, documents: list[str], metadatas: list[dict] | None = None
    ) -> list[str]:
        """Store documents and aligned metadata; return IDs in input order."""
        ...

    @abstractmethod
    def similarity_search(self, query: str, k: int = 3) -> list[str]:
        """Return up to k relevant document texts, best matches first."""
        ...
