"""Ручная правка улучшенного текста — сценарий 7 задания.

Дополнительная возможность: пользователь видит, что сделал ИИ, и может
поправить результат перед скачиванием. Повторная обработка при этом не
запускается — модель уже отработала.
"""

from copy import deepcopy
from uuid import UUID

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

DRAFT = "кароче надо бы купить три компа, цена 180 000 рублей"


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Document] = {}

    async def add(self, document: Document) -> None:
        self.items[document.id] = deepcopy(document)

    async def get(self, document_id: UUID) -> Document | None:
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
        **_ignored: object,
    ) -> None:
        await process_draft(
            document_id,
            uow_factory,
            llm_client=FakeLLMClient(),
            cache=NullJsonCache(),
        )

    monkeypatch.setattr(router_module, "process_draft", process_immediately)
    app.dependency_overrides[get_unit_of_work_factory] = lambda: factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_unit_of_work_factory, None)


def create_document(client: TestClient) -> str:
    response = client.post(
        "/api/documents",
        json={"draft": DRAFT, "doc_type": "memo", "template_id": "classic"},
    )

    assert response.status_code == 202
    return response.json()["id"]


@pytest.mark.api
def test_manual_edit_replaces_improved_text(client: TestClient) -> None:
    document_id = create_document(client)

    response = client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "Прошу выделить средства на закупку техники."},
    )

    assert response.status_code == 200
    assert (
        response.json()["improved_text"]
        == "Прошу выделить средства на закупку техники."
    )


@pytest.mark.api
def test_manual_edit_survives_reload(client: TestClient) -> None:
    document_id = create_document(client)

    client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "Итоговый текст после правки."},
    )
    reloaded = client.get(f"/api/documents/{document_id}").json()

    assert reloaded["improved_text"] == "Итоговый текст после правки."


@pytest.mark.api
def test_manual_edit_does_not_touch_the_draft(client: TestClient) -> None:
    """Черновик неприкосновенен: на него опирается сценарий 6."""
    document_id = create_document(client)

    client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "Совершенно другой текст."},
    )

    assert client.get(f"/api/documents/{document_id}").json()["draft"] == DRAFT


@pytest.mark.api
def test_edited_text_goes_into_the_docx(client: TestClient) -> None:
    document_id = create_document(client)

    client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "УНИКАЛЬНЫЙ_МАРКЕР_ПРАВКИ"},
    )
    response = client.post(f"/api/documents/{document_id}/render")

    assert response.status_code == 200

    from io import BytesIO

    from docx import Document as DocxDocument

    text = "\n".join(p.text for p in DocxDocument(BytesIO(response.content)).paragraphs)

    assert "УНИКАЛЬНЫЙ_МАРКЕР_ПРАВКИ" in text


@pytest.mark.api
def test_empty_text_is_rejected(client: TestClient) -> None:
    document_id = create_document(client)

    response = client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "   "},
    )

    assert response.status_code == 422


@pytest.mark.api
def test_edit_of_unknown_document_is_404(client: TestClient) -> None:
    response = client.patch(
        "/api/documents/00000000-0000-0000-0000-000000000000/text",
        json={"improved_text": "Текст"},
    )

    assert response.status_code == 404


@pytest.mark.api
def test_manual_edit_is_recorded_in_trace(client: TestClient) -> None:
    """Критерий 4.4: правку человека должно быть видно в журнале обработки."""
    document_id = create_document(client)

    client.patch(
        f"/api/documents/{document_id}/text",
        json={"improved_text": "Текст после ручной правки."},
    )
    attempts = client.get(f"/api/trace/{document_id}").json()
    stages = [stage["stage"] for attempt in attempts for stage in attempt["stages"]]

    assert "user_edit" in stages
