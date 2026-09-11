from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.documents.domain.entities import Document, Requisite
from src.modules.documents.domain.enums import (
    DocType,
    DocumentStatus,
    ProcessingStage,
    RequisiteStatus,
)
from src.modules.documents.infra.models import DocumentModel


class SQLAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(_to_model(document))

    async def get(
        self,
        document_id: UUID,
    ) -> Document | None:
        statement = select(DocumentModel).where(DocumentModel.id == document_id)

        row = (await self._session.execute(statement)).scalar_one_or_none()

        return _to_domain(row) if row is not None else None

    async def update(self, document: Document) -> None:
        await self._session.merge(_to_model(document))


def _to_model(doc: Document) -> DocumentModel:
    return DocumentModel(
        id=doc.id,
        draft=doc.draft,
        doc_type=doc.doc_type.value,
        template_id=doc.template_id,
        status=doc.status.value,
        stage=(doc.stage.value if doc.stage is not None else None),
        improved_text=doc.improved_text,
        changes=list(doc.changes),
        requisites=[
            {
                "key": requisite.key,
                "label": requisite.label,
                "value": requisite.value,
                "status": requisite.status.value,
                "required": requisite.required,
            }
            for requisite in doc.requisites
        ],
        fact_guard=(dict(doc.fact_guard) if doc.fact_guard is not None else None),
        is_fallback=doc.is_fallback,
        error=(dict(doc.error) if doc.error is not None else None),
        created_at=doc.created_at,
    )


def _to_domain(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        draft=row.draft,
        doc_type=DocType(row.doc_type),
        template_id=row.template_id,
        status=DocumentStatus(row.status),
        stage=(ProcessingStage(row.stage) if row.stage is not None else None),
        improved_text=row.improved_text,
        changes=list(row.changes or []),
        requisites=[
            Requisite(
                key=item["key"],
                label=item["label"],
                value=item.get("value"),
                status=RequisiteStatus(item["status"]),
                required=item["required"],
            )
            for item in row.requisites or []
        ],
        fact_guard=(dict(row.fact_guard) if row.fact_guard is not None else None),
        is_fallback=row.is_fallback,
        error=(dict(row.error) if row.error is not None else None),
        created_at=row.created_at,
    )
