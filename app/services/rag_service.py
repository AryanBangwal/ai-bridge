"""Context augmentation layered over the existing provider-neutral AI service."""

from app.rag.base import BaseVectorStore
from app.services.ai_service import AIService


class RAGService:
    def __init__(self, ai_service: AIService, vector_store: BaseVectorStore) -> None:
        self.ai_service = ai_service
        self.vector_store = vector_store

    def generate(
        self,
        query: str,
        explicit_context: str | None = None,
        use_rag: bool = False,
        k: int = 3,
        max_context_chars: int = 16000,
    ) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a nonblank string")
        if explicit_context is not None and not isinstance(explicit_context, str):
            raise ValueError("Explicit context must be a string")
        if type(use_rag) is not bool:
            raise ValueError("use_rag must be a boolean")
        if type(k) is not int or k < 1:
            raise ValueError("k must be a positive integer")
        if type(max_context_chars) is not int or max_context_chars < 1:
            raise ValueError("max_context_chars must be a positive integer")
        chunks = []
        if explicit_context and explicit_context.strip():
            chunks.append(explicit_context.strip())
        if use_rag:
            chunks.extend(self.vector_store.similarity_search(query, k=k))
        context = "\n\n".join(chunks)[:max_context_chars].rstrip()
        prompt = (
            f"Context:\n{context}\n\nQuestion: {query.strip()}"
            if context
            else query.strip()
        )
        return self.ai_service.generate(prompt)
