from typing import Protocol, Self

from src.modules.documents.application.ports.document_repository import (
    DocumentRepository,
)


class UnitOfWork(Protocol):
    """Единая транзакционная граница.

    Новый модуль -> добавить сюда атрибут с типом порта репозитория,
    а в SQLAlchemyUnitOfWork.__aenter__ - его создание.
    """

    documents: DocumentRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type, exc_value, traceback): ...

    async def commit(self): ...

    async def rollback(self): ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
