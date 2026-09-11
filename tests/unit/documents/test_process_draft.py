from copy import deepcopy
from uuid import UUID

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from src.modules.documents.application.handlers.process_draft import run
from src.modules.documents.application.ports.llm_client import LLMResult
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import DocumentStatus
from src.modules.documents.domain.exceptions import LLMUnavailable
from src.modules.documents.infra import trace_store
from src.shared.application.cache import NullJsonCache
from src.shared.infra.redis.json_cache import RedisJsonCache
from tests.fakes import FakeLLMClient, FakeUoW, FakeUoWFactory


class InMemoryDocumentRepository:
    def __init__(self, document: Document) -> None:
        self.items: dict[UUID, Document] = {
            document.id: deepcopy(document),
        }

    async def add(self, document: Document) -> None:
        self.items[document.id] = deepcopy(document)

    async def get(
        self,
        document_id: UUID,
    ) -> Document | None:
        document = self.items.get(document_id)

        return deepcopy(document) if document is not None else None

    async def update(self, document: Document) -> None:
        self.items[document.id] = deepcopy(document)


class InMemoryJsonCache:
    """Простейший рабочий JsonCache для проверки повторных запросов."""

    def __init__(self) -> None:
        self.store: dict[str, object] = {}

    async def get_json(self, key: str):
        return self.store.get(key)

    async def set_json(self, key: str, value, *, ttl_seconds: int) -> bool:
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed

    async def delete_by_pattern(self, pattern: str) -> int:
        return 0


class _BrokenRedis:
    """Имитирует недоступный Redis на уровне клиента redis-py."""

    async def get(self, key: str):
        raise RedisConnectionError("соединение с Redis недоступно")

    async def set(self, key: str, value: str, ex: int | None = None):
        raise RedisConnectionError("соединение с Redis недоступно")


def _factory(
    document: Document,
) -> tuple[FakeUoWFactory, InMemoryDocumentRepository]:
    repository = InMemoryDocumentRepository(document)
    factory = FakeUoWFactory(FakeUoW(documents=repository))
    return factory, repository


@pytest.mark.unit
@pytest.mark.asyncio
async def test_successful_response_marks_processed() -> None:
    document = Document(draft="Текст черновика")
    factory, repository = _factory(document)
    llm = FakeLLMClient(
        result=LLMResult(
            improved_text="Улучшенный текст",
            requisites={},
            changes=[],
            fact_guard={"verdict": "clean"},
            is_fallback=False,
        )
    )

    await run(document.id, factory, llm_client=llm, cache=NullJsonCache())

    saved = await repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.PROCESSED
    assert saved.stage is None
    assert saved.improved_text == "Улучшенный текст"
    assert saved.draft == "Текст черновика"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_unavailable_marks_failed_and_keeps_draft() -> None:
    draft = "Черновик, который нельзя терять"
    document = Document(draft=draft)
    factory, repository = _factory(document)
    llm = FakeLLMClient(exception=LLMUnavailable("нет соединения с ml_service"))

    await run(document.id, factory, llm_client=llm, cache=NullJsonCache())

    saved = await repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.FAILED
    assert saved.draft == draft
    assert saved.error is not None
    assert saved.error["code"] == "llm_unavailable"
    assert saved.error["recoverable"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_result_marks_degraded_not_processed() -> None:
    document = Document(draft="Текст")
    factory, repository = _factory(document)
    llm = FakeLLMClient(
        result=LLMResult(
            improved_text="Текст",
            requisites={},
            changes=[],
            fact_guard={"verdict": "clean"},
            is_fallback=True,
        )
    )

    await run(document.id, factory, llm_client=llm, cache=NullJsonCache())

    saved = await repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.DEGRADED
    assert saved.is_fallback is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repeated_request_hits_cache_and_skips_llm() -> None:
    document = Document(draft="Один и тот же текст")
    factory, repository = _factory(document)
    llm = FakeLLMClient(
        result=LLMResult(
            improved_text="Готовый результат",
            requisites={},
            changes=[],
            fact_guard={"verdict": "clean"},
            is_fallback=False,
        )
    )
    cache = InMemoryJsonCache()

    await run(document.id, factory, llm_client=llm, cache=cache)
    await run(document.id, factory, llm_client=llm, cache=cache)

    assert len(llm.calls) == 1

    saved = await repository.get(document.id)
    assert saved is not None
    assert saved.status == DocumentStatus.PROCESSED
    assert saved.improved_text == "Готовый результат"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_outage_does_not_block_processing() -> None:
    document = Document(draft="Текст")
    factory, repository = _factory(document)
    llm = FakeLLMClient()
    cache = RedisJsonCache(redis=_BrokenRedis(), key_prefix="app")

    await run(document.id, factory, llm_client=llm, cache=cache)

    saved = await repository.get(document.id)
    assert saved is not None
    assert saved.status == DocumentStatus.PROCESSED
    assert len(llm.calls) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_has_all_stages_after_success() -> None:
    document = Document(draft="Текст")
    factory, _ = _factory(document)
    llm = FakeLLMClient()

    await run(document.id, factory, llm_client=llm, cache=NullJsonCache())

    stages = [entry["stage"] for entry in trace_store.get(document.id)]
    assert stages == ["llm_request", "llm_raw", "fact_guard", "validation"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unexpected_exception_marks_failed_not_crashes() -> None:
    """TL-06: не только LLMUnavailable - любая неожиданная ошибка в

    пайплайне (например, баг в клиенте или в самой обработке) не должна
    ронять фоновый таск наружу - документ уходит в failed с code="internal",
    draft остаётся на месте.
    """

    draft = "Черновик, который нельзя терять"
    document = Document(draft=draft)
    factory, repository = _factory(document)
    llm = FakeLLMClient(exception=RuntimeError("неожиданная ошибка в клиенте"))

    # run() не должен выбросить исключение наружу - именно это и проверяем.
    await run(document.id, factory, llm_client=llm, cache=NullJsonCache())

    saved = await repository.get(document.id)

    assert saved is not None
    assert saved.status == DocumentStatus.FAILED
    assert saved.draft == draft
    assert saved.error is not None
    assert saved.error["code"] == "internal"
    assert saved.error["recoverable"] is True

    stages = [entry["stage"] for entry in trace_store.get(document.id)]
    assert stages[-1] == "pipeline_error"
