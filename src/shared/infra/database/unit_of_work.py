from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.documents.infra.repositories import SQLAlchemyDocumentRepository
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.outbox.infra.repositories import SQLAlchemyOutboxRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.documents = SQLAlchemyDocumentRepository(self.session)
        self.outbox = SQLAlchemyOutboxRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()
