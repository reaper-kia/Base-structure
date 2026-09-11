import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from urllib.parse import quote

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)

from src.modules.documents.infra import trace_store
from src.modules.documents.infra.llm_http_client import HttpLLMClient
from src.modules.templates.application.renderer import TemplateDocxRenderer
from src.shared.infra.redis.json_cache import RedisJsonCache
from src.core.config import settings
from src.modules.documents.api.schemas import (
    CreateDocumentRequest,
    DocumentResponse,
    DocTypeRequisiteResponse,
    DocTypeResponse,
    RequisiteSchema,
    ToggleAiFailureRequest,
    UpdateRequisitesRequest,
)
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.application.ports.docx_renderer import DocxRenderer
from src.modules.documents.application.services.doc_type_registry import (
    get_doc_type,
    list_doc_types as load_doc_types,
)
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import (
    DocType,
    DocumentStatus,
    ProcessingStage,
    RequisiteStatus,
)
from src.modules.documents.domain.exceptions import DocTypeNotFound
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.unit_of_work import UnitOfWorkFactory
from src.shared.infra.redis.client import redis_client

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# TL-07: контент-диспозишн отдаём только латиницей - старые Safari ломают
# кириллицу в имени файла (contracts/api.md §4). Обычная практическая
# транслитерация, не ГОСТ - для имени файла точность звука не нужна.
_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

router = APIRouter(
    prefix="/api",
    tags=["documents"],
)


def _template_exists(template_id: str) -> bool:
    if Path(template_id).name != template_id:
        return False

    rules_path = Path(settings.templates_dir) / template_id / "rules.yaml"

    return rules_path.is_file()


def _schedule_processing(
    background_tasks: BackgroundTasks,
    document_id: UUID,
    uow_factory: UnitOfWorkFactory,
) -> None:
    background_tasks.add_task(
        process_draft,
        document_id,
        uow_factory,
        llm_client=HttpLLMClient(),
        cache=RedisJsonCache(
            redis=redis_client,
            key_prefix=settings.redis_key_prefix,
        ),
    )


def _get_docx_renderer() -> DocxRenderer:
    # Отдельная фабрика (а не TemplateDocxRenderer() прямо в теле хендлера) -
    # чтобы тесты могли подменить router_module._get_docx_renderer на
    # FakeDocxRenderer, не трогая fastapi/TestClient.
    return TemplateDocxRenderer()


def _transliterate(text: str) -> str:
    return "".join(_TRANSLIT.get(ch, ch) for ch in text.lower())


def _render_filename(doc_type_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _transliterate(doc_type_name)).strip("-")
    today = datetime.now(UTC).strftime("%d-%m-%Y")

    return f"{slug}-{today}.docx"


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        status=document.status.value,
        stage=(document.stage.value if document.stage is not None else None),
        doc_type=document.doc_type.value,
        template_id=document.template_id,
        draft=document.draft,
        improved_text=document.improved_text,
        changes=list(document.changes),
        requisites=[
            RequisiteSchema(
                key=requisite.key,
                label=requisite.label,
                value=requisite.value,
                status=requisite.status.value,
                required=requisite.required,
            )
            for requisite in document.requisites
        ],
        fact_guard=document.fact_guard,
        is_fallback=document.is_fallback,
        error=document.error,
    )


@router.get(
    "/doc-types",
    response_model=list[DocTypeResponse],
)
async def list_doc_types() -> list[DocTypeResponse]:
    return [
        DocTypeResponse(
            id=spec.id,
            name=spec.name,
            description=spec.description,
            requisites=[
                DocTypeRequisiteResponse(
                    key=requisite.key,
                    label=requisite.label,
                    required=requisite.required,
                )
                for requisite in spec.requisites
            ],
        )
        for spec in load_doc_types()
    ]


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_document(
    payload: CreateDocumentRequest,
    background_tasks: BackgroundTasks,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    try:
        get_doc_type(payload.doc_type)
    except DocTypeNotFound as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail="Неизвестный тип документа",
        ) from exc

    if not _template_exists(payload.template_id):
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail="Неизвестный шаблон оформления",
        )

    document = Document(
        draft=payload.draft,
        doc_type=DocType(payload.doc_type),
        template_id=payload.template_id,
    )

    async with uow_factory() as uow:
        await uow.documents.add(document)
        await uow.commit()

    _schedule_processing(background_tasks, document.id, uow_factory)

    return _to_response(document)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    return _to_response(document)


@router.patch(
    "/documents/{document_id}/requisites",
    response_model=DocumentResponse,
)
async def update_requisites(
    document_id: UUID,
    payload: UpdateRequisitesRequest,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден",
            )

        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Документ ещё обрабатывается",
            )

        schema_keys = {
            requisite.key
            for requisite in get_doc_type(document.doc_type.value).requisites
        }
        requisites_by_key = {
            requisite.key: requisite for requisite in document.requisites
        }

        for key, raw_value in payload.values.items():
            if key not in schema_keys:
                # Реквизит вне схемы типа документа - молча игнорируем.
                continue

            requisite = requisites_by_key.get(key)
            if requisite is None:
                continue

            value = raw_value.strip() if isinstance(raw_value, str) else raw_value
            # Пустая строка после strip() - это "оставить пустым", а не значение.
            value = value or None

            if value is None:
                requisite.value = None
                requisite.status = RequisiteStatus.LEFT_BLANK
            else:
                requisite.value = value
                requisite.status = RequisiteStatus.USER_PROVIDED

        await uow.documents.update(document)
        await uow.commit()

    return _to_response(document)


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    """Сценарий 6, кнопка «Повторить».

    draft не трогаем, реквизиты со статусом user_provided/left_blank
    сохранятся сами - за это отвечает requisites_validator.validate(
    existing=...), вызываемый внутри run().
    """

    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден",
            )

        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Документ уже обрабатывается",
            )

        document.status = DocumentStatus.PROCESSING
        document.stage = ProcessingStage.LLM
        document.error = None

        await uow.documents.update(document)
        await uow.commit()

    _schedule_processing(background_tasks, document.id, uow_factory)

    return _to_response(document)


@router.post("/documents/{document_id}/render")
async def render_document(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> Response:
    """Сценарий 1, финальный шаг. contracts/api.md §4.

    Сам рендер - не мой код (TL-07 прямо запрещает его писать, это B2), моя
    часть - статусы/зависимость/заголовки. TemplateDocxRenderer.render()
    сейчас NotImplementedError("TODO(B2)") - до готовности B2-03 этот
    эндпоинт будет отдавать 500 вместо файла, это ожидаемо.
    """

    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    if document.status in (DocumentStatus.PROCESSING, DocumentStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Документ ещё не обработан",
        )

    # Сюда доходят только processed/degraded - process_draft.finish()
    # всегда выставляет improved_text вместе с этими статусами, так что
    # None здесь означал бы сломанный инвариант, а не штатный случай.
    spec = get_doc_type(document.doc_type.value)
    result = _get_docx_renderer().render(
        document.improved_text,
        document.requisites,
        document.template_id,
    )

    filename = _render_filename(spec.name)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    if result.template_fallback_used:
        headers["X-Template-Fallback"] = "true"
        if result.template_fallback_reason:
            headers["X-Template-Fallback-Reason"] = quote(
                result.template_fallback_reason
            )

    return Response(
        content=result.content,
        media_type=DOCX_MEDIA_TYPE,
        headers=headers,
    )


@router.get("/trace/{document_id}")
async def get_trace(
    document_id: UUID,
) -> list[dict]:
    """Критерий 4.4: журнал шагов ИИ-обработки, in-memory, без авторизации."""

    return trace_store.get(document_id)


@router.post("/dev/break-ai")
async def toggle_ai_failure(
    payload: ToggleAiFailureRequest,
) -> dict:
    """Тумблер для сценария 6 - эксперт ломает ИИ своими руками.

    Не прячем за паролем и не убираем из прода: смысл именно в том, чтобы
    эксперт сам включил отказ и увидел честную деградацию, а не рассказ
    словами. Переключает settings.ai_force_failure в рантайме - его же
    проверяет HttpLLMClient перед каждым запросом к ml_service.
    """

    settings.ai_force_failure = payload.enabled

    return {"ai_force_failure": settings.ai_force_failure}


def _templates_loaded() -> list[str]:
    templates_dir = Path(settings.templates_dir)

    if not templates_dir.is_dir():
        return []

    return sorted(
        entry.name
        for entry in templates_dir.iterdir()
        if entry.is_dir() and (entry / "rules.yaml").is_file()
    )


@router.get("/dev/state")
async def get_dev_state() -> dict:
    """Диагностика для фронта и команды.

    Фронту нужен для положения тумблера после перезагрузки, команде - чтобы
    за секунду понять перед демо, всё ли поднялось.
    """

    ml_reachable = False
    model_version = "unknown"

    if settings.ml_service_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.ml_service_url}/health/model")
                response.raise_for_status()
                payload = response.json()
        except Exception:  # noqa: BLE001
            # dev/state - диагностический эндпоинт, он не имеет права упасть
            # из-за того, что ml_service сейчас не отвечает.
            pass
        else:
            ml_reachable = bool(payload.get("model_loaded", False))
            model_version = payload.get("model_version", model_version)

    return {
        "ai_force_failure": settings.ai_force_failure,
        "ml_service_url": settings.ml_service_url,
        "ml_reachable": ml_reachable,
        "model_version": model_version,
        "templates_loaded": _templates_loaded(),
    }
