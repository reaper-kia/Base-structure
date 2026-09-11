from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.documents.domain.entities import Document
from src.modules.documents.infra.models import DocumentModel


class SQLAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(_to_model(document))

    async def get(self, document_id: UUID) -> Document | None:
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, document: Document) -> None:
        await self._session.merge(_to_model(document))


def _to_model(doc: Document) -> DocumentModel:
    raise NotImplementedError("TODO(TL): маппинг Document -> DocumentModel")


def _to_domain(row: DocumentModel) -> Document:
    raise NotImplementedError("TODO(TL): маппинг DocumentModel -> Document")
