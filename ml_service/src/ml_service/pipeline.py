"""Слой надёжности между «модель ответила» и «вернули бэкенду».

contracts/llm_contract.md §4: четыре шага — принуждение к JSON, repair-проход,
Fact Guard, fallback. Здесь же считаются latency_ms и reason_code.

Философия §3.2: changes — украшение, его потеря не ломает продукт;
improved_text и requisites — суть, их потеря означает провал обработки.
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

from ml_service import fallback
from ml_service.config import settings
from ml_service.guard import anchors, fact_guard
from ml_service.llm import schema as llm_schema
from ml_service.llm.ollama import (
    OllamaClient,
    OllamaUnavailableError,
    build_process_prompt,
    build_repair_prompt,
)
from ml_service.rag.retriever import RetrievedChunk, format_retrieved_context
from ml_service.rag.runtime import knowledge_retriever
from ml_service.schemas import FactGuardResult, ProcessRequest, ProcessResponse

logger = logging.getLogger(__name__)

FALLBACK_VERSION = "rule-based-1.1.0"


class ModelUnavailable(RuntimeError):
    """Модель недоступна, а fallback выключен -> 503 (§2)."""


class Retriever(Protocol):
    async def retrieve(self, query: str) -> list[RetrievedChunk]: ...


def _retrieval_query(request: ProcessRequest) -> str:
    """Собирает запрос без расширения публичного HTTP-контракта."""
    return "\n".join(
        (
            request.doc_type_name,
            request.structure_hint,
            # Ollama умеет truncate, но ограничение здесь также ускоряет
            # lexical fallback на максимально допустимом черновике.
            request.draft[:6000],
        )
    )


async def _knowledge_context(
    request: ProcessRequest,
    retriever: Retriever,
) -> str:
    try:
        chunks = await retriever.retrieve(_retrieval_query(request))
    except Exception as exc:  # noqa: BLE001 - RAG обязан деградировать без отказа
        logger.warning("RAG недоступен, продолжаю без контекста: %s", exc)
        return ""

    return format_retrieved_context(
        chunks,
        max_chars=settings.rag_max_context_chars,
    )


def _guard_of(
    draft: str,
    improved_text: str,
    requisites: dict[str, str | None],
    source_anchors: dict,
) -> fact_guard.GuardResult:
    """Сверяем черновик со ВСЕМ, что уйдёт в документ.

    Реквизиты — такая же часть результата, как и текст: адресат уезжает из
    тела в поле, и если смотреть только на improved_text, каждый вынесенный
    реквизит выглядел бы потерянным фактом.
    """
    result_text = "\n".join(
        [improved_text, *[value for value in requisites.values() if value]]
    )

    return fact_guard.check(
        source_anchors,
        anchors.extract(result_text),
        source_text=draft,
    )


async def _ask_model(
    client: OllamaClient,
    prompt: str,
    response_schema: dict,
    requisite_keys: list[str],
) -> dict | None:
    """Шаг 1 + шаг 2: вызов модели и починка ответа.

    Возвращает разобранный словарь или None, если починить не удалось.
    """
    raw = await client.generate(prompt, response_schema)

    parsed = llm_schema.extract_json(raw)
    if parsed is not None:
        return parsed

    if not settings.repair_enabled:
        return None

    logger.warning("Ответ модели не разобрался как JSON, запускаю repair-проход")

    try:
        repaired_raw = await client.generate(
            build_repair_prompt(raw, requisite_keys),
            response_schema,
        )
    except OllamaUnavailableError as exc:
        logger.warning("Repair-проход не удался: %s", exc)
        return None

    return llm_schema.extract_json(repaired_raw)


async def process(
    request: ProcessRequest,
    client: OllamaClient | None = None,
    retriever: Retriever | None = None,
) -> ProcessResponse:
    started = time.perf_counter()
    client = client or OllamaClient()

    knowledge_context = ""
    if settings.rag_enabled:
        knowledge_context = await _knowledge_context(
            request,
            retriever or knowledge_retriever,
        )

    source_anchors = anchors.extract(request.draft)
    response_schema = llm_schema.build_response_schema(request.requisite_keys)
    prompt = build_process_prompt(
        draft=request.draft,
        doc_type_name=request.doc_type_name,
        structure_hint=request.structure_hint,
        requisite_keys=request.requisite_keys,
        knowledge_context=knowledge_context,
    )

    reason_code = None

    for attempt in range(1, settings.max_attempts + 1):
        try:
            parsed = await _ask_model(
                client, prompt, response_schema, request.requisite_keys
            )
        except OllamaUnavailableError as exc:
            logger.warning("Попытка %s: модель недоступна (%s)", attempt, exc)
            reason_code = "model_unavailable"
            break

        if parsed is None or not llm_schema.validate_llm_response(
            parsed, request.requisite_keys
        ):
            logger.warning("Попытка %s: ответ не прошёл валидацию схемы", attempt)
            reason_code = "schema_invalid"
            continue

        normalized = llm_schema.normalize_llm_response(parsed, request.requisite_keys)

        if not normalized["improved_text"]:
            logger.warning("Попытка %s: модель вернула пустой improved_text", attempt)
            reason_code = "empty_text"
            continue

        guard = _guard_of(
            request.draft,
            normalized["improved_text"],
            normalized["requisites"],
            source_anchors,
        )

        if guard.verdict == "blocked":
            logger.warning(
                "Попытка %s: Fact Guard заблокировал ответ (added=%s, inverted=%s)",
                attempt,
                guard.added,
                guard.inverted,
            )
            reason_code = "facts_unverified"
            continue

        return ProcessResponse(
            request_id=request.request_id,
            improved_text=normalized["improved_text"],
            requisites=normalized["requisites"],
            changes=normalized["changes"],
            fact_guard=FactGuardResult(**guard.as_dict()),
            is_fallback=False,
            model_version=client.model,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            reason_code=None,
        )

    if not settings.fallback_enabled:
        raise ModelUnavailable("Модель недоступна и fallback отключён")

    logger.info("Переходим на rule-based fallback, причина: %s", reason_code)

    result = fallback.process(
        request.draft, request.requisite_keys, request.structure_hint
    )
    guard = _guard_of(
        request.draft,
        result["improved_text"],
        result["requisites"],
        source_anchors,
    )

    return ProcessResponse(
        request_id=request.request_id,
        improved_text=result["improved_text"],
        requisites=result["requisites"],
        changes=result["changes"],
        fact_guard=FactGuardResult(**guard.as_dict()),
        is_fallback=True,
        model_version=FALLBACK_VERSION,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        reason_code=reason_code or "model_unavailable",
    )
