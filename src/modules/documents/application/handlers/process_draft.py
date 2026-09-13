"""Оркестратор пайплайна обработки черновика.

Кэш повторных запросов учитывает версию промпта, обходит кэш при явном
повторе и не кэширует надолго резервные (неуспешные) результаты.

Каждая попытка обработки пишется в журнал отдельно (по attempt_id),
с таймингами стадий, версиями модели/промпта и признаком попадания в кэш.

Имитация отказа ИИ (TL-14) фиксируется в метаданных попытки, чтобы её
можно было отличить от реальной поломки.
"""

import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.core.config import settings
from src.modules.documents.application.ports.llm_client import (
    LLMClient,
    LLMResult,
)
from src.modules.documents.application.services.doc_type_registry import (
    get_doc_type,
)
from src.modules.documents.application.services.requisites_validator import (
    validate,
)
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import (
    DocumentStatus,
    ProcessingStage,
)
from src.modules.documents.domain.exceptions import (
    DocumentNotFound,
    LLMUnavailable,
)
from src.modules.documents.infra import trace_store
from src.shared.application.cache import JsonCache
from src.shared.application.unit_of_work import UnitOfWorkFactory

logger = logging.getLogger(__name__)


async def _change_document(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory,
    change: Callable[[Document], None],
) -> Document:
    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

        if document is None:
            raise DocumentNotFound

        change(document)

        await uow.documents.update(document)
        await uow.commit()

        return document


def _cache_key(draft: str, doc_type: str) -> str:
    payload = f"{draft}{doc_type}{settings.prompt_version}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"llm:{digest}"


def _draft_fingerprint(draft: str) -> dict:
    """Обезличенный отпечаток входа для журнала: хеш и длина."""
    return {
        "sha256": hashlib.sha256(draft.encode()).hexdigest(),
        "length": len(draft),
    }


async def _mark_failed(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory,
    *,
    code: str,
    message: str,
) -> None:
    def mark_failed(doc: Document) -> None:
        doc.status = DocumentStatus.FAILED
        doc.stage = None
        doc.deadline = None
        doc.error = {
            "code": code,
            "message": message,
            "recoverable": True,
        }

    await _change_document(document_id, uow_factory, mark_failed)


async def run(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory,
    *,
    llm_client: LLMClient,
    cache: JsonCache,
    bypass_cache: bool = False,
    ai_force_failure: bool = False,
) -> None:
    """llm -> fact_guard -> validation."""

    def start(doc: Document) -> None:
        doc.status = DocumentStatus.PROCESSING
        doc.stage = ProcessingStage.LLM
        doc.error = None
        doc.reason_code = None
        now = datetime.now(UTC)
        doc.started_at = now
        doc.deadline = now + timedelta(seconds=settings.processing_deadline_seconds)

    document = await _change_document(document_id, uow_factory, start)

    attempt_id = trace_store.start_attempt(
        document_id,
        meta={
            "input": _draft_fingerprint(document.draft),
            "doc_type": document.doc_type.value,
            "template_id": document.template_id,
            "channel": document.channel.value,
            "prompt_version": settings.prompt_version,
            "bypass_cache": bypass_cache,
            # TL-14: помечаем, что попытка запущена с имитацией отказа.
            "ai_force_failure": ai_force_failure,
        },
    )

    try:
        spec = get_doc_type(document.doc_type.value)
        requisite_keys = [item.key for item in spec.requisites]

        trace_store.record(
            document_id,
            attempt_id,
            "llm_request",
            {
                "draft": document.draft,
                "doc_type": document.doc_type.value,
                "doc_type_name": spec.name,
                "structure_hint": spec.structure_hint,
                "requisite_keys": requisite_keys,
            },
        )

        cache_key = _cache_key(document.draft, document.doc_type.value)
        cached_payload = None

        if not bypass_cache:
            cached_payload = await cache.get_json(cache_key)

        llm_duration_ms: float | None = None

        if isinstance(cached_payload, dict):
            result = LLMResult(**cached_payload)
            trace_store.record(
                document_id,
                attempt_id,
                "cache_hit",
                {"cache_key": cache_key, "cache_hit": True},
            )
        else:
            llm_started = time.perf_counter()
            try:
                result = await llm_client.process(
                    draft=document.draft,
                    doc_type=document.doc_type.value,
                    doc_type_name=spec.name,
                    structure_hint=spec.structure_hint,
                    requisite_keys=requisite_keys,
                )
            except LLMUnavailable as exc:
                llm_duration_ms = (time.perf_counter() - llm_started) * 1000
                trace_store.record(
                    document_id,
                    attempt_id,
                    "llm_error",
                    {
                        "detail": str(exc),
                        # TL-14: отказ помечен как имитация, чтобы не
                        # спутать демо с реальной поломкой.
                        "simulated": ai_force_failure,
                    },
                    duration_ms=round(llm_duration_ms, 2),
                )
                trace_store.finish_attempt(document_id, attempt_id, outcome="failed")
                await _mark_failed(
                    document_id,
                    uow_factory,
                    code="llm_unavailable",
                    message=(
                        "ИИ-компонент недоступен. Черновик сохранён, "
                        "попробуйте ещё раз."
                    ),
                )
                return

            llm_duration_ms = (time.perf_counter() - llm_started) * 1000

            ttl = (
                settings.fallback_cache_ttl_seconds
                if result.is_fallback
                else settings.cache_ttl_seconds
            )
            await cache.set_json(
                cache_key,
                asdict(result),
                ttl_seconds=ttl,
            )
            trace_store.record(
                document_id,
                attempt_id,
                "cache_miss",
                {"cache_key": cache_key, "cache_hit": False},
            )

        trace_store.update_attempt_meta(
            document_id, attempt_id, model_version=result.model_version
        )

        trace_store.record(
            document_id,
            attempt_id,
            "llm_result",
            asdict(result),
            duration_ms=(
                round(llm_duration_ms, 2) if llm_duration_ms is not None else None
            ),
        )

        await _change_document(
            document_id,
            uow_factory,
            lambda doc: setattr(doc, "stage", ProcessingStage.FACT_GUARD),
        )

        trace_store.record(document_id, attempt_id, "fact_guard", result.fact_guard)

        await _change_document(
            document_id,
            uow_factory,
            lambda doc: setattr(doc, "stage", ProcessingStage.VALIDATION),
        )

        validated_requisites = validate(
            document.doc_type.value,
            result.requisites,
            existing=document.requisites,
        )

        trace_store.record(
            document_id,
            attempt_id,
            "validation",
            {
                "missing": [
                    item.key
                    for item in validated_requisites
                    if item.status.value == "missing"
                ],
                "auto_filled": [
                    item.key
                    for item in validated_requisites
                    if item.status.value == "auto_filled"
                ],
            },
        )

        def finish(doc: Document) -> None:
            doc.requisites = validated_requisites
            doc.improved_text = result.improved_text
            doc.changes = result.changes
            doc.fact_guard = result.fact_guard
            doc.is_fallback = result.is_fallback
            doc.reason_code = result.reason_code
            doc.status = (
                DocumentStatus.DEGRADED
                if result.is_fallback
                else DocumentStatus.PROCESSED
            )
            doc.stage = None
            doc.deadline = None

        await _change_document(document_id, uow_factory, finish)

        trace_store.finish_attempt(
            document_id,
            attempt_id,
            outcome="degraded" if result.is_fallback else "processed",
        )

    except DocumentNotFound:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Пайплайн обработки документа %s упал", document_id)
        trace_store.record(
            document_id,
            attempt_id,
            "pipeline_error",
            {"detail": str(exc)},
        )
        trace_store.finish_attempt(document_id, attempt_id, outcome="failed")
        await _mark_failed(
            document_id,
            uow_factory,
            code="internal",
            message=(
                "Внутренняя ошибка обработки. Черновик сохранён, попробуйте ещё раз."
            ),
        )
