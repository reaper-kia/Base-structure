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
from src.modules.documents.domain.enums import DocumentStatus
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
        # FakeLLMClient() без result ничего не находит по реквизитам (кроме
        # doc_date - он auto_fillable), так что addressee/position/... после
        # обработки уходят в missing - удобная база для тестов PATCH.
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


def create_processed_document(
    client: TestClient,
    draft: str = "Прошу предоставить отпуск",
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
def test_missing_addressee_after_processing_then_patch_sets_value(
    client: TestClient,
) -> None:
    """DoD TL-05: черновик без адресата -> жёлтый статус -> PATCH -> значение в ответе."""

    created = create_processed_document(client)

    before = client.get(f"/api/documents/{created['id']}").json()
    addressee_before = next(r for r in before["requisites"] if r["key"] == "addressee")
    assert addressee_before["status"] == "missing"

    response = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={"values": {"addressee": "Директору ООО «Ромашка» Петрову П.П."}},
    )

    assert response.status_code == 200
    addressee_after = next(
        r for r in response.json()["requisites"] if r["key"] == "addressee"
    )
    assert addressee_after["status"] == "user_provided"
    assert addressee_after["value"] == "Директору ООО «Ромашка» Петрову П.П."


@pytest.mark.api
def test_patch_with_null_sets_left_blank(
    client: TestClient,
) -> None:
    created = create_processed_document(client)

    response = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={"values": {"position": None}},
    )

    assert response.status_code == 200
    position = next(r for r in response.json()["requisites"] if r["key"] == "position")
    assert position["status"] == "left_blank"
    assert position["value"] is None


@pytest.mark.api
def test_patch_with_blank_string_is_treated_as_null(
    client: TestClient,
) -> None:
    created = create_processed_document(client)

    response = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={"values": {"executor": "   "}},
    )

    assert response.status_code == 200
    executor = next(r for r in response.json()["requisites"] if r["key"] == "executor")
    assert executor["status"] == "left_blank"
    assert executor["value"] is None


@pytest.mark.api
def test_patch_with_unknown_key_is_ignored_silently(
    client: TestClient,
) -> None:
    created = create_processed_document(client)

    response = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={
            "values": {
                "unknown_key": "что-то",
                "addressee": "Директору",
            }
        },
    )

    assert response.status_code == 200
    keys = {r["key"] for r in response.json()["requisites"]}
    assert "unknown_key" not in keys
    addressee = next(
        r for r in response.json()["requisites"] if r["key"] == "addressee"
    )
    assert addressee["status"] == "user_provided"


@pytest.mark.api
def test_patch_leaves_unmentioned_keys_untouched(
    client: TestClient,
) -> None:
    created = create_processed_document(client)
    before = client.get(f"/api/documents/{created['id']}").json()
    subject_before = next(r for r in before["requisites"] if r["key"] == "subject")

    client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={"values": {"addressee": "Директору"}},
    )

    after = client.get(f"/api/documents/{created['id']}").json()
    subject_after = next(r for r in after["requisites"] if r["key"] == "subject")

    assert subject_after == subject_before


@pytest.mark.api
def test_confirmed_registry_value_gets_distinct_status(
    client: TestClient,
) -> None:
    created = create_processed_document(client)

    response = client.patch(
        f"/api/documents/{created['id']}/requisites",
        json={
            "values": {"addressee": "Иванов Иван Иванович"},
            "from_registry": ["addressee"],
        },
    )

    assert response.status_code == 200
    addressee = next(
        item for item in response.json()["requisites"] if item["key"] == "addressee"
    )
    assert addressee["status"] == "from_registry"


@pytest.mark.api
def test_patch_while_processing_returns_409(
    client: TestClient,
    repository: InMemoryDocumentRepository,
) -> None:
    document = Document(draft="Текст", status=DocumentStatus.PROCESSING)
    repository.items[document.id] = document

    response = client.patch(
        f"/api/documents/{document.id}/requisites",
        json={"values": {"addressee": "Директору"}},
    )

    assert response.status_code == 409


@pytest.mark.api
def test_patch_unknown_document_returns_404(
    client: TestClient,
) -> None:
    response = client.patch(
        f"/api/documents/{uuid4()}/requisites",
        json={"values": {"addressee": "Директору"}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Документ не найден"}
