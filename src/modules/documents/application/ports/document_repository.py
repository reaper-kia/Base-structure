from typing import Protocol
from uuid import UUID

from src.modules.documents.domain.entities import Document


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...

    async def get(self, document_id: UUID) -> Document | None: ...

    async def update(self, document: Document) -> None: ...
