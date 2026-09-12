import re
from datetime import UTC, datetime
from uuid import UUID
from urllib.parse import quote

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from src.core.config import settings
from src.modules.documents.api.dependencies import (
    check_deadline,
    get_docx_renderer,
    schedule_processing,
    template_exists,
    templates_loaded,
)
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.api.dev_sessions import (
    COOKIE_NAME,
    get_ai_force_failure,
    resolve_session_id,
    set_ai_force_failure,
)
from src.modules.documents.api.schemas import (
    CreateDocumentRequest,
    DocumentResponse,
    DocTypeRequisiteResponse,
    DocTypeResponse,
    RequisiteSchema,
    ToggleAiFailureRequest,
    UpdateRequisitesRequest,
)
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
from src.modules.documents.infra import trace_store
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.unit_of_work import UnitOfWorkFactory

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

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


def _get_docx_renderer():
    """Стабильная точка подмены рендерера в API-тестах."""
    return get_docx_renderer()


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
    request: Request,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    try:
        get_doc_type(payload.doc_type)
    except DocTypeNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Неизвестный тип документа",
        ) from exc

    if not template_exists(payload.template_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

    session_id, _ = resolve_session_id(
        request.cookies.get(COOKIE_NAME)
    )
    ai_force_failure = get_ai_force_failure(session_id)

    schedule_processing(
        background_tasks,
        document.id,
        uow_factory,
        ai_force_failure=ai_force_failure,
        processor=process_draft,
    )

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

        if check_deadline(document):
            await uow.documents.update(document)
            await uow.commit()

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

        if check_deadline(document):
            await uow.documents.update(document)
            await uow.commit()

        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Документ ещё обрабатывается",
            )

        schema_keys = {
            requisite.key
            for requisite in get_doc_type(
                document.doc_type.value
            ).requisites
        }
        requisites_by_key = {
            requisite.key: requisite
            for requisite in document.requisites
        }

        for key, raw_value in payload.values.items():
            if key not in schema_keys:
                continue

            requisite = requisites_by_key.get(key)
            if requisite is None:
                continue

            value = (
                raw_value.strip()
                if isinstance(raw_value, str)
                else raw_value
            )
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
    request: Request,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> DocumentResponse:
    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден",
            )

        if check_deadline(document):
            await uow.documents.update(document)
            await uow.commit()

        if document.status == DocumentStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Документ уже обрабатывается. "
                    "Дождитесь завершения или таймаута."
                ),
            )

        document.status = DocumentStatus.PROCESSING
        document.stage = ProcessingStage.LLM
        document.error = None

        await uow.documents.update(document)
        await uow.commit()

    session_id, _ = resolve_session_id(
        request.cookies.get(COOKIE_NAME)
    )
    ai_force_failure = get_ai_force_failure(session_id)

    schedule_processing(
        background_tasks,
        document.id,
        uow_factory,
        bypass_cache=True,
        ai_force_failure=ai_force_failure,
        processor=process_draft,
    )

    return _to_response(document)


@router.post("/documents/{document_id}/render")
async def render_document(
    document_id: UUID,
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> Response:
    """Генерирует DOCX по выбранному шаблону."""
    async with uow_factory() as uow:
        document = await uow.documents.get(document_id)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден",
            )

        if check_deadline(document):
            await uow.documents.update(document)
            await uow.commit()

    if document.status in (
        DocumentStatus.PROCESSING,
        DocumentStatus.FAILED,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Документ ещё не обработан",
        )

    spec = get_doc_type(document.doc_type.value)

    try:
        result = _get_docx_renderer().render(
            document.improved_text,
            document.requisites,
            document.template_id,
        )
    except Exception as exc:  # noqa: BLE001
        trace_store.record_render(
            document_id,
            {
                "template_id": document.template_id,
                "error": str(exc),
            },
        )
        raise

    filename = _render_filename(spec.name)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{filename}"'
        )
    }

    if result.template_fallback_used:
        headers["X-Template-Fallback"] = "true"
        if result.template_fallback_reason:
            headers["X-Template-Fallback-Reason"] = quote(
                result.template_fallback_reason
            )

    trace_store.record_render(
        document_id,
        {
            "template_id": document.template_id,
            "filename": filename,
            "template_fallback_used": (
                result.template_fallback_used
            ),
            "template_fallback_reason": (
                result.template_fallback_reason
            ),
        },
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
    """Возвращает журнал попыток обработки документа."""
    return trace_store.get(document_id)


@router.post("/dev/break-ai")
async def toggle_ai_failure(
    payload: ToggleAiFailureRequest,
    request: Request,
    response: Response,
) -> dict:
    """Переключает имитацию отказа ИИ для текущей сессии."""
    session_id, is_new = resolve_session_id(
        request.cookies.get(COOKIE_NAME)
    )
    set_ai_force_failure(session_id, payload.enabled)

    if is_new:
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24,
        )

    return {"ai_force_failure": payload.enabled}


@router.get("/dev/state")
async def get_dev_state(request: Request) -> dict:
    """Возвращает диагностическое состояние текущей сессии."""
    session_id, _ = resolve_session_id(
        request.cookies.get(COOKIE_NAME)
    )
    ai_force_failure = get_ai_force_failure(session_id)

    ml_reachable = False
    model_version = "unknown"

    if settings.ml_service_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"{settings.ml_service_url}/health/model"
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:  # noqa: BLE001
            pass
        else:
            ml_reachable = bool(
                payload.get("model_loaded", False)
            )
            model_version = payload.get(
                "model_version",
                model_version,
            )

    return {
        "ai_force_failure": ai_force_failure,
        "ml_service_url": settings.ml_service_url,
        "ml_reachable": ml_reachable,
        "model_version": model_version,
        "templates_loaded": templates_loaded(),
    }