from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks

from src.core.config import settings
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.application.ports.docx_renderer import DocxRenderer
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import DocumentStatus
from src.modules.documents.infra.llm_http_client import HttpLLMClient
from src.modules.templates.application.renderer import TemplateDocxRenderer
from src.modules.templates.application.template_service import TemplateLoader
from src.shared.application.unit_of_work import UnitOfWorkFactory
from src.shared.infra.redis.client import redis_client
from src.shared.infra.redis.json_cache import RedisJsonCache

ProcessingHandler = Callable[..., Awaitable[None]]


def template_exists(template_id: str) -> bool:
    """Есть ли такой шаблон — среди встроенных или загруженных пользователем."""
    if Path(template_id).name != template_id:
        return False

    return template_id in templates_loaded()


def schedule_processing(
    background_tasks: BackgroundTasks,
    document_id: UUID,
    uow_factory: UnitOfWorkFactory,
    bypass_cache: bool = False,
    ai_force_failure: bool = False,
    processor: ProcessingHandler = process_draft,
) -> None:
    """Запускает фоновую обработку документа.

    `ai_force_failure` фиксируется на момент запроса и передаётся в фон:
    именно так имитация отказа, включённая экспертом, влияет на его документ,
    даже если фоновая задача стартует позже (см. TL-14).
    """
    background_tasks.add_task(
        processor,
        document_id,
        uow_factory,
        llm_client=HttpLLMClient(ai_force_failure=ai_force_failure),
        cache=RedisJsonCache(
            redis=redis_client,
            key_prefix=settings.redis_key_prefix,
        ),
        bypass_cache=bypass_cache,
        ai_force_failure=ai_force_failure,
    )


def get_docx_renderer() -> DocxRenderer:
    """Фабрика рендерера DOCX. Вынесена для возможности подмены в тестах."""
    return TemplateDocxRenderer()


def check_deadline(document: Document) -> bool:
    """Если дедлайн истёк, принудительно переводит документ в failed."""
    if document.status == DocumentStatus.PROCESSING and document.deadline is not None:
        if datetime.now(UTC) > document.deadline:
            document.status = DocumentStatus.FAILED
            document.stage = None
            document.deadline = None
            document.error = {
                "code": "timeout",
                "message": (
                    "Превышено время ожидания обработки. Попробуйте повторить."
                ),
                "recoverable": True,
            }
            return True
    return False


def templates_loaded() -> list[str]:
    """Идентификаторы доступных шаблонов: встроенные плюс пользовательские."""
    return sorted(
        template.id
        for template in TemplateLoader(settings.templates_dir).list_templates()
    )
