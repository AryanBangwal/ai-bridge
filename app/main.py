"""AI Bridge HTTP API. Run with python -m app.main."""

import logging
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    model_validator,
)

from app.config import settings
from app.providers.errors import (
    InvalidProviderError,
    ProviderConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.factory import ProviderFactory
from app.rag.base import BaseVectorStore
from app.rag.memory_store import InMemoryVectorStore
from app.services.ai_service import AIService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
app = FastAPI(title="AI Bridge", version="1.0.0")
app.state.vector_store = InMemoryVectorStore()


Selection = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


class PromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Selection | None = None
    model: Selection | None = None
    prompt: Annotated[
        str,
        StringConstraints(
            strict=True, strip_whitespace=True, min_length=1, max_length=32000
        ),
    ]


class PromptResponse(BaseModel):
    response: Annotated[str, StringConstraints(strict=True, min_length=1)]


DocumentText = Annotated[
    str,
    StringConstraints(
        strict=True, strip_whitespace=True, min_length=1, max_length=32000
    ),
]


class ContextQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: DocumentText
    provider: Selection | None = None
    model: Selection | None = None
    explicit_context: (
        Annotated[str, StringConstraints(strict=True, max_length=64000)] | None
    ) = None
    use_rag: StrictBool = False
    k: Annotated[int, Field(strict=True, ge=1, le=20)] = 3
    max_context_chars: Annotated[int, Field(strict=True, ge=1, le=64000)] = 16000


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: Annotated[list[DocumentText], Field(min_length=1, max_length=100)]
    metadatas: list[dict] | None = None

    @model_validator(mode="after")
    def validate_metadata_length(self):
        if self.metadatas is not None and len(self.metadatas) != len(self.documents):
            raise ValueError("Metadata must contain one dictionary per document")
        return self


class IngestResponse(BaseModel):
    ids: list[str]
    count: int


def get_vector_store(request: Request) -> BaseVectorStore:
    return request.app.state.vector_store


def get_rag_service(
    body: ContextQueryRequest,
    store: Annotated[BaseVectorStore, Depends(get_vector_store)],
) -> RAGService:
    service = AIService(ProviderFactory.get_provider(body.provider, body.model))
    return RAGService(service, store)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    configuration: Literal["valid"] = "valid"
    environment: str
    provider: str = "ollama"
    model: str


class ErrorResponse(BaseModel):
    detail: str


def get_ai_service(body: PromptRequest) -> AIService:
    return AIService(provider=ProviderFactory.get_provider(body.provider, body.model))


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    if isinstance(exc, InvalidProviderError):
        status_code = 400
    elif isinstance(exc, (ProviderConfigurationError, ProviderUnavailableError)):
        status_code = 503
    elif isinstance(exc, ProviderTimeoutError):
        status_code = 504
    else:
        status_code = 502
    logger.warning("Provider failure: %s", type(exc).__name__)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled API failure", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """API liveness and startup configuration status; does not probe Ollama."""
    provider = ProviderFactory.get_provider()
    return HealthResponse(
        environment=settings.APP_ENV,
        provider=settings.DEFAULT_PROVIDER,
        model=getattr(provider, "model", settings.DEFAULT_MODEL),
    )


@app.post(
    "/api/v1/generate",
    response_model=PromptResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 500, 502, 503, 504)},
)
def generate(
    body: PromptRequest, service: Annotated[AIService, Depends(get_ai_service)]
) -> PromptResponse:
    # Sync routes keep blocking provider I/O in FastAPI's worker pool.
    return PromptResponse(response=service.generate(body.prompt))


@app.post(
    "/api/v1/generate-with-context",
    response_model=PromptResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 500, 502, 503, 504)},
)
def generate_with_context(
    body: ContextQueryRequest, service: Annotated[RAGService, Depends(get_rag_service)]
) -> PromptResponse:
    return PromptResponse(
        response=service.generate(
            body.query,
            explicit_context=body.explicit_context,
            use_rag=body.use_rag,
            k=body.k,
            max_context_chars=body.max_context_chars,
        )
    )


@app.post("/api/v1/rag/ingest", response_model=IngestResponse, status_code=201)
def ingest(
    body: IngestRequest, store: Annotated[BaseVectorStore, Depends(get_vector_store)]
) -> IngestResponse:
    ids = store.add_documents(body.documents, body.metadatas)
    return IngestResponse(ids=ids, count=len(ids))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
