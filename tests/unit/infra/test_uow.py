from unittest.mock import AsyncMock, MagicMock

import pytest

from src.shared.infra.database.unit_of_work import SQLAlchemyUnitOfWork


def _fake_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sqlalchemy_uow_initializes_all_repositories() -> None:
    """Добавил репозиторий в UoW - допиши сюда assert, иначе рассинхрон
    протокола и реализации не будет замечен."""
    session = _fake_session()
    uow = SQLAlchemyUnitOfWork(MagicMock(return_value=session))

    entered = await uow.__aenter__()

    assert entered is uow
    assert uow.documents is not None
    assert uow.outbox is not None

    await uow.__aexit__(None, None, None)
    session.close.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sqlalchemy_uow_rolls_back_on_exception() -> None:
    session = _fake_session()
    uow = SQLAlchemyUnitOfWork(MagicMock(return_value=session))
    await uow.__aenter__()

    await uow.__aexit__(RuntimeError, RuntimeError("boom"), None)

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sqlalchemy_uow_commits_and_flushes() -> None:
    session = _fake_session()
    session.flush = AsyncMock()
    uow = SQLAlchemyUnitOfWork(MagicMock(return_value=session))
    await uow.__aenter__()

    await uow.commit()
    await uow.flush()

    session.commit.assert_awaited_once()
    session.flush.assert_awaited_once()
