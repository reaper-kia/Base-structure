"""Локальный RAG-индекс с vector search и лексическим fallback."""

from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from ml_service.rag.chunker import KnowledgeChunk, chunk_document
from ml_service.rag.embedder import EmbeddingUnavailable

_SUPPORTED_SUFFIXES = frozenset({".md", ".txt"})
_TOKEN = re.compile(r"[0-9a-zа-яё]{3,}", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
        "без",
        "был",
        "для",
        "его",
        "или",
        "как",
        "при",
        "это",
        "этот",
        "эта",
        "что",
    }
)

RetrievalMethod = Literal["vector", "lexical"]
RagState = Literal["not_ready", "empty", "ready"]


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    doc_id: str
    position: int
    section_title: str
    text: str
    doc_hash: str
    score: float
    method: RetrievalMethod


@dataclass(frozen=True, slots=True)
class RagStatus:
    state: RagState
    knowledge_files: int
    indexed_chunks: int
    vector_available: bool
    last_method: RetrievalMethod | None
    last_error: str | None


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (
        left_norm * right_norm
    )


def _tokens(text: str) -> set[str]:
    result: set[str] = set()
    for raw in _TOKEN.findall(text.casefold().replace("ё", "е")):
        if raw in _STOP_WORDS:
            continue
        # Общий префикс помогает русским падежам без тяжёлого NLP:
        # «отпуск», «отпуске» и «отпуска» дают один поисковый токен.
        result.add(raw[:5] if len(raw) > 5 else raw)
    return result


def _lexical_similarity(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / math.sqrt(
        len(query_tokens) * len(text_tokens)
    )


class KnowledgeRetriever:
    def __init__(
        self,
        *,
        knowledge_dir: Path,
        embedder: Embedder | None,
        top_k: int = 3,
        min_vector_score: float = 0.2,
        embedding_batch_size: int = 32,
        max_files: int = 100,
        max_chunks: int = 500,
        max_file_bytes: int = 1_000_000,
    ) -> None:
        if top_k <= 0 or embedding_batch_size <= 0:
            raise ValueError("top_k and embedding_batch_size must be positive")
        if max_files <= 0 or max_chunks <= 0 or max_file_bytes <= 0:
            raise ValueError("knowledge limits must be positive")
        if not 0.0 <= min_vector_score <= 1.0:
            raise ValueError("min_vector_score must be between 0 and 1")

        self._knowledge_dir = knowledge_dir
        self._embedder = embedder
        self._top_k = top_k
        self._min_vector_score = min_vector_score
        self._embedding_batch_size = embedding_batch_size
        self._max_files = max_files
        self._max_chunks = max_chunks
        self._max_file_bytes = max_file_bytes

        self._manifest: tuple[tuple[str, int, int], ...] | None = None
        self._chunks: list[KnowledgeChunk] = []
        self._vectors: list[list[float]] | None = None
        self._vector_failed = False
        self._vector_retry_at = 0.0
        self._knowledge_files = 0
        self._last_method: RetrievalMethod | None = None
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    def status(self) -> RagStatus:
        if self._manifest is None:
            state: RagState = "not_ready"
        elif not self._chunks:
            state = "empty"
        else:
            state = "ready"
        return RagStatus(
            state=state,
            knowledge_files=self._knowledge_files,
            indexed_chunks=len(self._chunks),
            vector_available=self._vectors is not None,
            last_method=self._last_method,
            last_error=self._last_error,
        )

    async def refresh(self) -> RagStatus:
        """Обновляет файловый индекс без обращения к embedding-модели."""
        async with self._lock:
            self._reload_if_changed()
            return self.status()

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []

        async with self._lock:
            self._reload_if_changed()
            if not self._chunks:
                self._last_method = None
                return []

            vector_retry_due = (
                not self._vector_failed or time.monotonic() >= self._vector_retry_at
            )
            if self._embedder is not None and vector_retry_due:
                try:
                    await self._ensure_vectors()
                    query_vector = (await self._embedder.embed([query]))[0]
                    vector_result = self._rank_vector(query_vector)
                    if vector_result:
                        self._last_method = "vector"
                        self._last_error = None
                        return vector_result
                except Exception as exc:  # noqa: BLE001 - lexical fallback обязателен
                    # RAG не имеет права ломать основной сценарий. Если bge-m3
                    # не скачана, остаётся детерминированный lexical retrieval.
                    self._vector_failed = True
                    self._vector_retry_at = time.monotonic() + 60.0
                    self._vectors = None
                    self._last_error = str(exc)[:500]

            self._last_method = "lexical"
            return self._rank_lexical(query)

    def _knowledge_files_with_manifest(
        self,
    ) -> tuple[list[Path], tuple[tuple[str, int, int], ...]]:
        if not self._knowledge_dir.is_dir():
            return [], ()

        files: list[Path] = []
        manifest: list[tuple[str, int, int]] = []
        for path in sorted(self._knowledge_dir.rglob("*")):
            if len(files) >= self._max_files:
                break
            if (
                path.is_symlink()
                or not path.is_file()
                or path.suffix.casefold() not in _SUPPORTED_SUFFIXES
            ):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size > self._max_file_bytes:
                continue
            files.append(path)
            manifest.append(
                (
                    path.relative_to(self._knowledge_dir).as_posix(),
                    stat.st_size,
                    stat.st_mtime_ns,
                )
            )
        return files, tuple(manifest)

    def _reload_if_changed(self) -> None:
        files, manifest = self._knowledge_files_with_manifest()
        if manifest == self._manifest:
            return

        chunks: list[KnowledgeChunk] = []
        accepted_files = 0
        last_error: str | None = None

        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                last_error = f"cannot read {path.name}: {exc}"
                continue

            document_chunks = chunk_document(
                text,
                doc_id=path.relative_to(self._knowledge_dir).as_posix(),
            )
            if document_chunks:
                accepted_files += 1
            remaining = self._max_chunks - len(chunks)
            chunks.extend(document_chunks[:remaining])
            if len(chunks) >= self._max_chunks:
                break

        self._manifest = manifest
        self._chunks = chunks
        self._vectors = None
        self._vector_failed = False
        self._vector_retry_at = 0.0
        self._knowledge_files = accepted_files
        self._last_method = None
        self._last_error = last_error

    async def _ensure_vectors(self) -> None:
        if self._vectors is not None:
            return
        if self._embedder is None:
            raise EmbeddingUnavailable("vector retrieval is disabled")

        vectors: list[list[float]] = []
        texts = [chunk.text for chunk in self._chunks]
        for offset in range(0, len(texts), self._embedding_batch_size):
            vectors.extend(
                await self._embedder.embed(
                    texts[offset : offset + self._embedding_batch_size]
                )
            )
        if len(vectors) != len(self._chunks):
            raise EmbeddingUnavailable("embedding index is incomplete")
        self._vectors = vectors

    def _rank_vector(self, query_vector: list[float]) -> list[RetrievedChunk]:
        if self._vectors is None:
            return []
        scored = [
            (cosine_similarity(query_vector, vector), chunk)
            for chunk, vector in zip(self._chunks, self._vectors, strict=True)
        ]
        return self._top_results(
            scored, method="vector", minimum=self._min_vector_score
        )

    def _rank_lexical(self, query: str) -> list[RetrievedChunk]:
        scored = [
            (_lexical_similarity(query, chunk.text), chunk) for chunk in self._chunks
        ]
        return self._top_results(scored, method="lexical", minimum=0.0)

    def _top_results(
        self,
        scored: list[tuple[float, KnowledgeChunk]],
        *,
        method: RetrievalMethod,
        minimum: float,
    ) -> list[RetrievedChunk]:
        ranked = sorted(
            (item for item in scored if item[0] > minimum),
            key=lambda item: (-item[0], item[1].doc_id, item[1].position),
        )[: self._top_k]
        return [
            RetrievedChunk(
                doc_id=chunk.doc_id,
                position=chunk.position,
                section_title=chunk.section_title,
                text=chunk.text,
                doc_hash=chunk.doc_hash,
                score=round(score, 6),
                method=method,
            )
            for score, chunk in ranked
        ]


def format_retrieved_context(
    chunks: list[RetrievedChunk],
    *,
    max_chars: int,
) -> str:
    """Формирует ограниченный по размеру блок с явным происхождением."""
    if max_chars <= 0:
        return ""

    blocks: list[str] = []
    used = 0
    for chunk in chunks:
        safe_doc_id = (
            chunk.doc_id.replace(chr(0), "")
            .replace("===", "≡≡≡")
            .replace("\r", " ")
            .replace("\n", " ")
        )
        safe_section = (
            (chunk.section_title or "без раздела")
            .replace(chr(0), "")
            .replace("===", "≡≡≡")
            .replace("\r", " ")
            .replace("\n", " ")
        )
        # Справочник контролируется владельцем стенда, но всё равно не может
        # закрыть системные маркеры и выйти из своего блока промпта.
        safe_text = chunk.text.replace(chr(0), "").replace("===", "≡≡≡")
        block = f"[Источник: {safe_doc_id}; раздел: {safe_section}]\n" f"{safe_text}"
        separator_size = 2 if blocks else 0
        remaining = max_chars - used - separator_size
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[: max(0, remaining - 1)].rstrip() + "…"
        blocks.append(block)
        used += separator_size + len(block)

    return "\n\n".join(blocks)
