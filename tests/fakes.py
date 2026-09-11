from types import TracebackType
from typing import Any, Self
from unittest.mock import AsyncMock


class FakeUoW:
    """Small asynchronous unit-of-work double shared by unit tests."""

    def __init__(self, *, documents: Any, outbox: Any | None = None) -> None:
        self.documents = documents
        self.outbox = outbox
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class FakeUoWFactory:
    def __init__(self, uow: FakeUoW) -> None:
        self._uow = uow

    def __call__(self) -> FakeUoW:
        return self._uow
