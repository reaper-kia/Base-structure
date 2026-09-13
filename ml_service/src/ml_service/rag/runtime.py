"""Сконфигурированный RAG-индекс процесса ml_service."""

from pathlib import Path

from ml_service.config import settings
from ml_service.rag.embedder import OllamaEmbedder
from ml_service.rag.retriever import KnowledgeRetriever

_SERVICE_ROOT = Path(__file__).resolve().parents[3]


def _knowledge_dir(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else _SERVICE_ROOT / path


embedder = (
    OllamaEmbedder(
        base_url=settings.ollama_url,
        model=settings.rag_embed_model,
        timeout_seconds=settings.rag_embed_timeout_seconds,
        keep_alive=settings.rag_embed_keep_alive,
    )
    if settings.rag_vector_enabled
    else None
)

knowledge_retriever = KnowledgeRetriever(
    knowledge_dir=_knowledge_dir(settings.rag_knowledge_dir),
    embedder=embedder,
    top_k=settings.rag_top_k,
    min_vector_score=settings.rag_min_score,
)
