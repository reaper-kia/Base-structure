from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import src.modules.documents.api.router as router_module
from src.main import app
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.domain.entities import Document
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.cache import NullJsonCache
from tests.fakes import FakeLLMClient, FakeUoW, FakeUoWFactory


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Document] = {}

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


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    repository = InMemoryDocumentRepository()

    factory = FakeUoWFactory(FakeUoW(documents=repository))

    async def process_immediately(
        document_id: UUID,
        uow_factory: FakeUoWFactory,
        **_ignored_kwargs: object,
    ) -> None:
        # Реальный роутер передаёт сюда HttpLLMClient/RedisJsonCache - в
        # тесте жизненного цикла (без сети и Redis) подменяем их фейками,
        # игнорируя то, что прислал роутер через add_task(..., llm_client=,
        # cache=).
        await process_draft(
            document_id,
            uow_factory,
            llm_client=FakeLLMClient(),
            cache=NullJsonCache(),
        )

    monkeypatch.setattr(
        router_module,
        "process_draft",
        process_immediately,
    )

    app.dependency_overrides[get_unit_of_work_factory] = lambda: factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(
        get_unit_of_work_factory,
        None,
    )


def create_document(
    client: TestClient,
    draft: str = "Исходный текст",
) -> dict:
    response = client.post(
        "/api/documents",
        json={
            "draft": draft,
            "doc_type": "memo",
            "template_id": "classic",
        },
    )

    assert response.status_code == 202
    return response.json()


@pytest.mark.api
def test_create_document_returns_processing(
    client: TestClient,
) -> None:
    payload = create_document(client)

    assert payload["status"] == "processing"
    assert payload["stage"] == "llm"
    assert payload["channel"] == "web"


@pytest.mark.api
def test_bot_channel_is_persisted_and_visible_in_trace(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/documents",
        json={
            "draft": "Текст из бота",
            "doc_type": "memo",
            "template_id": "classic",
            "channel": "bot",
        },
    )

    assert response.status_code == 202
    document_id = response.json()["id"]
    assert response.json()["channel"] == "bot"
    assert client.get(f"/api/documents/{document_id}").json()["channel"] == "bot"
    attempts = client.get(f"/api/trace/{document_id}").json()
    assert attempts[-1]["channel"] == "bot"


@pytest.mark.api
def test_document_becomes_processed(
    client: TestClient,
) -> None:
    created = create_document(client)

    response = client.get(f"/api/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["stage"] is None
    assert response.json()["improved_text"] == "Исходный текст"


@pytest.mark.api
def test_draft_is_preserved_byte_for_byte(
    client: TestClient,
) -> None:
    draft = "  Первая строка\nВторая строка  "
    created = create_document(client, draft)

    response = client.get(f"/api/documents/{created['id']}")

    assert response.json()["draft"] == draft


@pytest.mark.api
def test_blank_draft_returns_422(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/documents",
        json={
            "draft": "   \n  ",
            "doc_type": "memo",
            "template_id": "classic",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_unknown_doc_type_returns_422(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/documents",
        json={
            "draft": "Текст",
            "doc_type": "unknown",
            "template_id": "classic",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_unknown_template_returns_422(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/documents",
        json={
            "draft": "Текст",
            "doc_type": "memo",
            "template_id": "unknown",
        },
    )

    assert response.status_code == 422


@pytest.mark.api
def test_unknown_document_returns_russian_404(
    client: TestClient,
) -> None:
    response = client.get(f"/api/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Документ не найден"}
