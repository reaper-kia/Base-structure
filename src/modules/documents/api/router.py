from uuid import UUID

from fastapi import APIRouter

from src.modules.documents.api.schemas import (
    CreateDocumentRequest,
    DocumentResponse,
    UpdateRequisitesRequest,
)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/doc-types")
async def list_doc_types() -> list[dict]:
    raise NotImplementedError("TODO(TL)")


@router.post("/documents", response_model=DocumentResponse)
async def create_document(payload: CreateDocumentRequest) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.patch("/documents/{document_id}/requisites", response_model=DocumentResponse)
async def update_requisites(
    document_id: UUID, payload: UpdateRequisitesRequest
) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.post("/documents/{document_id}/render")
async def render_document(document_id: UUID):
    raise NotImplementedError("TODO(TL)")


@router.get("/trace/{document_id}")
async def get_trace(document_id: UUID) -> list[dict]:
    raise NotImplementedError("TODO(TL)")


@router.post("/dev/break-ai")
async def toggle_ai_failure(enabled: bool) -> dict:
    """Тумблер для сценария 6. Эксперт ломает ИИ своими руками."""
    raise NotImplementedError("TODO(TL)")
