"""TL-07: связка с рендерером. contracts/api.md §4, TLtasks.md §7.4.

TemplateDocxRenderer (B2, TODO(B2)) ещё не реализован, поэтому здесь везде
подменяем router_module._get_docx_renderer на FakeDocxRenderer - тестируем
только то, что реально моё: статусы/404/409, заголовки фолбэка, имя файла
в Content-Disposition. Сам рендер (сборка .docx по правилам шаблона) -
не мой код и не мои тесты, это TL-07 прямо запрещает переписывать.
"""

from copy import deepcopy
from uuid import UUID, uuid4
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

import src.modules.documents.api.router as router_module
from src.main import app
from src.modules.documents.application.handlers.process_draft import (
    run as process_draft,
)
from src.modules.documents.domain.entities import Document
from src.modules.documents.domain.enums import DocumentStatus
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.cache import NullJsonCache
from tests.fakes import FakeDocxRenderer, FakeLLMClient, FakeUoW, FakeUoWFactory


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
        await process_draft(
            document_id,
            uow_factory,
            llm_client=FakeLLMClient(),
            cache=NullJsonCache(),
        )

    monkeypatch.setattr(router_module, "process_draft", process_immediately)
    # По умолчанию - "успешный" рендерер без фолбэка; тесты, которым нужно
    # другое поведение (фолбэк, битый рендер), подменяют его сами.
    monkeypatch.setattr(router_module, "_get_docx_renderer", lambda: FakeDocxRenderer())

    app.dependency_overrides[get_unit_of_work_factory] = lambda: factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_unit_of_work_factory, None)


def create_processed_document(
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
def test_render_processed_returns_docx_with_pk_signature(
    client: TestClient,
) -> None:
    """Тест 1: processed -> 200 и непустой бинарник с сигнатурой PK."""

    created = create_processed_document(client)

    response = client.post(f"/api/documents/{created['id']}/render")

    assert response.status_code == 200
    assert response.content.startswith(b"PK")
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@pytest.mark.api
def test_render_processing_returns_409(
    client: TestClient,
    repository: InMemoryDocumentRepository,
) -> None:
    """Тест 2: processing -> 409."""

    document = Document(draft="Текст", status=DocumentStatus.PROCESSING)
    repository.items[document.id] = document

    response = client.post(f"/api/documents/{document.id}/render")

    assert response.status_code == 409


@pytest.mark.api
def test_render_failed_returns_409(
    client: TestClient,
    repository: InMemoryDocumentRepository,
) -> None:
    """Тест 3: failed -> 409."""

    document = Document(draft="Текст", status=DocumentStatus.FAILED)
    document.error = {
        "code": "llm_unavailable",
        "message": "x",
        "recoverable": True,
    }
    repository.items[document.id] = document

    response = client.post(f"/api/documents/{document.id}/render")

    assert response.status_code == 409


@pytest.mark.api
def test_render_degraded_returns_200(
    client: TestClient,
    repository: InMemoryDocumentRepository,
) -> None:
    """Тест 4: degraded -> 200, это разрешённое состояние."""

    document = Document(draft="Текст", status=DocumentStatus.DEGRADED)
    document.improved_text = "Текст"
    document.is_fallback = True
    repository.items[document.id] = document

    response = client.post(f"/api/documents/{document.id}/render")

    assert response.status_code == 200
    assert response.content.startswith(b"PK")


@pytest.mark.api
def test_render_with_broken_template_sets_fallback_headers(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Тест 5: повреждённый шаблон -> 200 + X-Template-Fallback."""

    reason = "Шаблон «modern» повреждён, применён «classic»"
    monkeypatch.setattr(
        router_module,
        "_get_docx_renderer",
        lambda: FakeDocxRenderer(
            template_fallback_used=True,
            template_fallback_reason=reason,
        ),
    )

    created = create_processed_document(client)
    response = client.post(f"/api/documents/{created['id']}/render")

    assert response.status_code == 200
    assert response.headers["x-template-fallback"] == "true"
    # Заголовок процент-закодирован (кириллица не проходит через latin-1
    # HTTP-заголовков) - фронт делает decodeURIComponent(), тест - unquote().
    assert unquote(response.headers["x-template-fallback-reason"]) == reason


@pytest.mark.api
def test_render_content_disposition_is_ascii_only(client: TestClient) -> None:
    """Тест 6: Content-Disposition содержит только латиницу и цифры."""

    created = create_processed_document(client)
    response = client.post(f"/api/documents/{created['id']}/render")

    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="')
    # Имя типа "Служебная записка" -> "sluzhebnaya-zapiska-DD-MM-YYYY.docx".
    filename = disposition.split('filename="')[1].rstrip('"')
    assert filename.encode("ascii")  # не бросает UnicodeEncodeError
    assert filename.startswith("sluzhebnaya-zapiska-")
    assert filename.endswith(".docx")


@pytest.mark.api
def test_render_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/documents/{uuid4()}/render")

    assert response.status_code == 404
    assert response.json() == {"detail": "Документ не найден"}
