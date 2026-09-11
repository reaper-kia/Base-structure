"""TL-04/TL-06: оркестратор пайплайна обработки черновика.

Реальная последовательность llm -> fact_guard -> validation (вместо
временной заглушки TL-03, которая просто ждала и копировала draft).
Кэш повторных запросов и клиент ИИ приходят снаружи (см. api/router.py) -
этот модуль знает только про их протоколы (LLMClient, JsonCache), не про
конкретные HTTP/Redis реализации.

TL-06: любое неожиданное исключение внутри пайплайна (не только
LLMUnavailable) переводит документ в failed вместо того, чтобы молча
уронить фоновый таск - сценарий 6, "исключение в пайплайне -> status=failed,
приложение живо".
"""

import hashlib
import logging
from collections.abc import Callable
from dataclasses import asdict
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
    # Формула из contracts/llm_contract.md §4.3: key = sha256(draft + doc_type).
    digest = hashlib.sha256(f"{draft}{doc_type}".encode()).hexdigest()
    return f"llm:{digest}"


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
) -> None:
    """llm -> fact_guard -> validation.

    draft не перезаписывается ни на одном шаге - это прямое требование
    сценария 6 ("сервис не теряет введённый пользователем текст").
    """

    def start(doc: Document) -> None:
        doc.status = DocumentStatus.PROCESSING
        doc.stage = ProcessingStage.LLM
        doc.error = None

    document = await _change_document(document_id, uow_factory, start)

    try:
        spec = get_doc_type(document.doc_type.value)
        requisite_keys = [item.key for item in spec.requisites]

        trace_store.record(
            document_id,
            "llm_request",
            {
                "doc_type": document.doc_type.value,
                "doc_type_name": spec.name,
                "structure_hint": spec.structure_hint,
                "requisite_keys": requisite_keys,
            },
        )

        cache_key = _cache_key(document.draft, document.doc_type.value)
        cached_payload = await cache.get_json(cache_key)

        if cached_payload is not None:
            result = LLMResult(**cached_payload)
        else:
            try:
                result = await llm_client.process(
                    draft=document.draft,
                    doc_type=document.doc_type.value,
                    doc_type_name=spec.name,
                    structure_hint=spec.structure_hint,
                    requisite_keys=requisite_keys,
                )
            except LLMUnavailable as exc:
                await _mark_failed(
                    document_id,
                    uow_factory,
                    code="llm_unavailable",
                    message=(
                        "ИИ-компонент недоступен. Черновик сохранён, "
                        "попробуйте ещё раз."
                    ),
                )
                trace_store.record(document_id, "llm_error", {"detail": str(exc)})
                return

            # Недоступность Redis не должна ломать обработку - JsonCache-
            # адаптеры (RedisJsonCache) сами глотают свои ошибки и
            # возвращают False/None, так что set_json здесь ничего не
            # проверяет и не падает.
            await cache.set_json(
                cache_key,
                asdict(result),
                ttl_seconds=settings.cache_ttl_seconds,
            )

        trace_store.record(document_id, "llm_raw", asdict(result))

        await _change_document(
            document_id,
            uow_factory,
            lambda doc: setattr(doc, "stage", ProcessingStage.FACT_GUARD),
        )

        trace_store.record(document_id, "fact_guard", result.fact_guard)

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
            # draft не перезаписываем.
            doc.requisites = validated_requisites
            doc.improved_text = result.improved_text
            doc.changes = result.changes
            doc.fact_guard = result.fact_guard
            doc.is_fallback = result.is_fallback
            doc.status = (
                DocumentStatus.DEGRADED
                if result.is_fallback
                else DocumentStatus.PROCESSED
            )
            doc.stage = None

        await _change_document(document_id, uow_factory, finish)

    except DocumentNotFound:
        # Документ исчез посреди обработки - пометить нечего, просто не
        # роняем фоновый таск наружу необработанным.
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Пайплайн обработки документа %s упал", document_id)
        await _mark_failed(
            document_id,
            uow_factory,
            code="internal",
            message=(
                "Внутренняя ошибка обработки. Черновик сохранён, попробуйте ещё раз."
            ),
        )
        trace_store.record(document_id, "pipeline_error", {"detail": str(exc)})
