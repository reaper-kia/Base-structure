"""TL-06: сценарий 6 - тумблер ИИ, reprocess, dev/state.

Тесты 3 и часть теста 6 (POST /render -> 409 при failed, «рендер работает»
при degraded) сюда намеренно не включены: /render - это TL-07, эндпоинт
всё ещё заглушка (NotImplementedError). Добавить их нужно будет вместе с
TL-07, не раньше.
"""

from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import src.modules.documents.api.router as router_module
from src.core.config import settings
from src.main import app
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import DocumentStatus
from src.modules.documents.domain.exceptions import LLMUnavailable
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
def repository() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    repository: InMemoryDocumentRepository,
):
    factory = FakeUoWFactory(FakeUoW(documents=repository))

    async def process_immediately(
        document_id: UUID,
        uow_factory: FakeUoWFactory,
        **_ignored_kwargs: object,
    ) -> None:
        # В проде именно HttpLLMClient.process() читает settings.ai_force_failure
        # и поднимает LLMUnavailable (src/modules/documents/infra/llm_http_client.py).
        # Мы подменяем только транспорт (HTTP -> FakeLLMClient), но решение
        # "включён ли тумблер" принимаем по тому же settings, иначе
        # POST /dev/break-ai в тестах ни на что бы не влиял.
        if settings.ai_force_failure:
            llm = FakeLLMClient(exception=LLMUnavailable("ИИ отключён вручную"))
        else:
            llm = FakeLLMClient()

        await process_draft(
            document_id,
            uow_factory,
            llm_client=llm,
            cache=NullJsonCache(),
        )

    monkeypatch.setattr(router_module, "process_draft", process_immediately)

    app.dependency_overrides[get_unit_of_work_factory] = lambda: factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_unit_of_work_factory, None)
    # settings - модульный синглтон, общий для всех тестов процесса: не
    # сбросим тумблер - следующий тест (в этом файле или в другом) унаследует
    # "сломанный" ИИ и упадёт по непонятной причине.
    settings.ai_force_failure = False


def create_document(
    client: TestClient,
    draft: str = "Прошу предоставить отпуск",
) -> dict:
    response = client.post(
        "/api/documents",
        json={"draft": draft, "doc_type": "memo", "template_id": "classic"},
    )
    assert response.status_code == 202
    return response.json()


@pytest.mark.api
def test_toggle_on_makes_processing_fail(client: TestClient) -> None:
    """Тест 1: эксперт включает тумблер -> новый документ уходит в failed."""

    toggle = client.post("/api/dev/break-ai", json={"enabled": True})
    assert toggle.status_code == 200
    assert toggle.json() == {"ai_force_failure": True}

    created = create_document(client)

    document = client.get(f"/api/documents/{created['id']}").json()
    assert document["status"] == "failed"
    assert document["error"]["code"] == "llm_unavailable"
    assert document["error"]["recoverable"] is True


@pytest.mark.api
def test_draft_survives_failure(client: TestClient) -> None:
    """Тест 2: черновик не теряется, даже когда обработка падает."""

    client.post("/api/dev/break-ai", json={"enabled": True})

    draft = "Черновик, который нельзя терять"
    created = create_document(client, draft=draft)

    document = client.get(f"/api/documents/{created['id']}").json()
    assert document["status"] == "failed"
    assert document["draft"] == draft


@pytest.mark.api
def test_reprocess_after_toggle_off_succeeds(client: TestClient) -> None:
    """Тест 4: чинят ИИ (тумблер выключен) -> «Повторить» -> processed."""

    client.post("/api/dev/break-ai", json={"enabled": True})
    created = create_document(client)
    failed = client.get(f"/api/documents/{created['id']}").json()
    assert failed["status"] == "failed"

    client.post("/api/dev/break-ai", json={"enabled": False})

    response = client.post(f"/api/documents/{created['id']}/reprocess")
    assert response.status_code == 202

    document = client.get(f"/api/documents/{created['id']}").json()
    assert document["status"] == "processed"
    assert document["error"] is None


@pytest.mark.api
def test_reprocess_preserves_user_decided_requisites(client: TestClient) -> None:
    """Тест 5: «Повторить» не затирает то, что пользователь решил в PATCH."""

    created = create_document(client)

    patched = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={
            "values": {
                "addressee": "Директору ООО «Ромашка»",
                "position": None,
            }
        },
    )
    assert patched.status_code == 200

    response = client.post(f"/api/documents/{created['id']}/reprocess")
    assert response.status_code == 202

    document = client.get(f"/api/documents/{created['id']}").json()
    assert document["status"] == "processed"

    addressee = next(r for r in document["requisites"] if r["key"] == "addressee")
    position = next(r for r in document["requisites"] if r["key"] == "position")
    assert addressee["status"] == "user_provided"
    assert addressee["value"] == "Директору ООО «Ромашка»"
    assert position["status"] == "left_blank"
    assert position["value"] is None


@pytest.mark.api
def test_reprocess_while_processing_returns_409(
    client: TestClient,
    repository: InMemoryDocumentRepository,
) -> None:
    document = Document(draft="Текст", status=DocumentStatus.PROCESSING)
    repository.items[document.id] = document

    response = client.post(f"/api/documents/{document.id}/reprocess")

    assert response.status_code == 409


@pytest.mark.api
def test_reprocess_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/documents/{uuid4()}/reprocess")

    assert response.status_code == 404
    assert response.json() == {"detail": "Документ не найден"}


@pytest.mark.api
def test_dev_state_reflects_toggle_position(client: TestClient) -> None:
    """Тест 7: GET /dev/state отражает текущее положение тумблера."""

    off = client.get("/api/dev/state")
    assert off.status_code == 200
    assert off.json()["ai_force_failure"] is False

    client.post("/api/dev/break-ai", json={"enabled": True})

    on = client.get("/api/dev/state")
    assert on.status_code == 200
    assert on.json()["ai_force_failure"] is True
    # Не завязываемся на доступность настоящего ml_service - в тестовом
    # окружении его нет и не должно быть, эндпоинт обязан это пережить.
    assert "ml_reachable" in on.json()
    assert "templates_loaded" in on.json()
