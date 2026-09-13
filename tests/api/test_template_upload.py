"""Загрузка произвольного DOCX-шаблона.

Расширение сверх обязательного минимума (задание, п. 1.6). Проверяется
главное: параметры реально вычитываются из файла, шаблон сразу становится
доступным для генерации, а встроенный шаблон подменить нельзя.
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.core import config
from src.main import app

ORGANIZER_TEMPLATE = Path(
    "docs/organizer-materials/шаблоны/Шаблон__Современный регламентный.docx"
)
ADMIN_TOKEN = "test-admin-secret-token-42"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Каталог пользовательских шаблонов уводим во временный: тест не должен
    # оставлять папки в репозитории.
    monkeypatch.setattr(
        config.settings, "user_templates_dir", str(tmp_path / "templates")
    )
    monkeypatch.setattr(config.settings, "admin_token", ADMIN_TOKEN)

    with TestClient(app) as test_client:
        yield test_client


def upload(client: TestClient, filename: str = "my-template.docx"):
    return client.post(
        "/api/templates/upload",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        files={
            "file": (
                filename,
                ORGANIZER_TEMPLATE.read_bytes(),
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
            )
        },
    )


@pytest.mark.api
def test_upload_reads_real_parameters_from_the_file(client: TestClient) -> None:
    response = upload(client)

    assert response.status_code == 201

    rules = response.json()["rules"]

    assert rules["font"]["family"] == "Arial"
    assert rules["font"]["size_pt"] == 12
    assert rules["page"]["left_mm"] == pytest.approx(25, abs=0.5)


@pytest.mark.api
def test_uploaded_template_becomes_available(client: TestClient) -> None:
    template_id = upload(client).json()["id"]

    templates = {t["id"]: t for t in client.get("/api/templates").json()["templates"]}

    assert template_id in templates
    assert templates[template_id]["available"] is True


@pytest.mark.api
def test_uploaded_template_is_accepted_when_creating_a_document(
    client: TestClient,
) -> None:
    """Шаблон должен проходить проверку покрытия обязательных реквизитов.

    Иначе `POST /api/documents` отклонил бы его как неизвестный ещё до
    обращения к базе.
    """
    from src.modules.documents.api.dependencies import template_exists

    template_id = upload(client).json()["id"]

    assert template_exists(template_id) is True


@pytest.mark.api
def test_builtin_template_cannot_be_shadowed(client: TestClient) -> None:
    """Иначе загрузкой файла можно было бы подменить classic для всех."""
    response = upload(client, filename="classic.docx")

    assert response.json()["id"] != "classic"


@pytest.mark.api
def test_placeholders_become_substitution_tokens(client: TestClient) -> None:
    """«[Название документа] | [Дата]» — это токены, а не текст колонтитула."""
    rules = upload(client).json()["rules"]
    footer = rules["header_footer"]["footer"]["text"]

    assert "{doc_date}" in footer
    assert "[" not in footer


@pytest.mark.api
def test_rules_are_written_next_to_the_file(client: TestClient) -> None:
    payload = upload(client).json()
    folder = Path(config.settings.user_templates_dir) / payload["id"]

    assert (folder / "template.docx").is_file()

    saved = yaml.safe_load((folder / "rules.yaml").read_text(encoding="utf-8"))

    assert saved["font"]["family"] == "Arial"


@pytest.mark.api
def test_not_a_docx_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/templates/upload",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        files={"file": ("fake.docx", b"not a zip at all", "application/octet-stream")},
    )

    assert response.status_code == 422


@pytest.mark.api
def test_upload_without_admin_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/templates/upload",
        files={
            "file": (
                "template.docx",
                ORGANIZER_TEMPLATE.read_bytes(),
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Недействительный ключ администратора"}


@pytest.mark.api
def test_upload_with_wrong_admin_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/templates/upload",
        headers={"X-Admin-Token": "wrong-token"},
        files={
            "file": (
                "template.docx",
                ORGANIZER_TEMPLATE.read_bytes(),
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 401


@pytest.mark.api
def test_empty_configured_admin_token_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config.settings, "admin_token", "")

    response = client.post(
        "/api/templates/upload",
        headers={"X-Admin-Token": "any-value"},
        files={
            "file": (
                "template.docx",
                ORGANIZER_TEMPLATE.read_bytes(),
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 401
