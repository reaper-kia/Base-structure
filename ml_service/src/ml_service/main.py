"""HTTP-фасад ml_service — contracts/llm_contract.md §2.

Сервис сознательно ничего не знает про типы документов: название типа,
подсказку по структуре и список ключей реквизитов присылает бэкенд. Добавить
пятый тип документа = поправить один YAML на бэкенде, сюда не заходить.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from ml_service.config import settings
from ml_service.llm.ollama import OllamaClient
from ml_service.pipeline import ModelUnavailable, process
from ml_service.rag.runtime import knowledge_retriever
from ml_service.schemas import ModelHealth, ProcessRequest, ProcessResponse, RagHealth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Всегда 200, даже без модели.

        Это осознанно: иначе Docker будет перезапускать контейнер, который
        работоспособен в режиме деградации (§2).
        """
        return {"status": "ok"}

    @app.get("/health/model", response_model=ModelHealth)
    async def model_health() -> ModelHealth:
        """Дёргается перед демонстрацией и отдаётся бэкендом в /api/dev/state."""
        client = OllamaClient()
        loaded, detail = await client.health()

        return ModelHealth(
            model_loaded=loaded,
            model_version=client.model,
            fallback_enabled=settings.fallback_enabled,
            supported_tasks=["process"],
            ollama_url=settings.ollama_url,
            detail=detail,
        )

    @app.get("/health/rag", response_model=RagHealth)
    async def rag_health() -> RagHealth:
        """Состояние локального индекса; отсутствие embeddings не авария."""
        if not settings.rag_enabled:
            return RagHealth(
                enabled=False,
                state="disabled",
                embedding_model=(
                    settings.rag_embed_model if settings.rag_vector_enabled else None
                ),
                knowledge_files=0,
                indexed_chunks=0,
                vector_available=False,
            )

        try:
            rag_status = await knowledge_retriever.refresh()
        except Exception as exc:  # noqa: BLE001 - health RAG не ломает сервис
            return RagHealth(
                enabled=True,
                state="not_ready",
                embedding_model=(
                    settings.rag_embed_model if settings.rag_vector_enabled else None
                ),
                knowledge_files=0,
                indexed_chunks=0,
                vector_available=False,
                last_error=str(exc)[:500],
            )
        return RagHealth(
            enabled=True,
            state=rag_status.state,
            embedding_model=(
                settings.rag_embed_model if settings.rag_vector_enabled else None
            ),
            knowledge_files=rag_status.knowledge_files,
            indexed_chunks=rag_status.indexed_chunks,
            vector_available=rag_status.vector_available,
            last_method=rag_status.last_method,
            last_error=rag_status.last_error,
        )

    @app.post("/api/v1/process", response_model=ProcessResponse)
    async def process_document(request: ProcessRequest) -> ProcessResponse:
        try:
            return await process(request)
        except ModelUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    return app


app = create_app()
