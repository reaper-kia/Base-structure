"""B2-13.3: гейт X-Admin-Token для POST /api/templates/upload.

ТЗ: 401 без/с неверным токеном, 201 с верным.
Пустой ADMIN_TOKEN в конфиге → загрузка закрыта (401), не открыта.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.core.config import settings
from src.main import app

ASSETS = Path("src/modules/templates/assets")
VALID_TOKEN = "test-admin-secret-token-42"


@pytest.fixture
def classic_docx_bytes() -> bytes:
    return (ASSETS / "classic" / "template.docx").read_bytes()


@pytest.fixture
def client_with_token():
    """Фикстура: settings.admin_token = VALID_TOKEN на время теста."""
    with patch.object(settings, "admin_token", VALID_TOKEN):
        yield TestClient(app)


@pytest.fixture
def client_empty_token():
    """Фикстура: settings.admin_token = '' (пустой → закрыто)."""
    with patch.object(settings, "admin_token", ""):
        yield TestClient(app)


def test_upload_without_token_returns_401(
    client_with_token, classic_docx_bytes
) -> None:
    resp = client_with_token.post(
        "/api/templates/upload",
        files={
            "file": ("classic.docx", classic_docx_bytes, "application/octet-stream")
        },
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Недействительный ключ администратора"}


def test_upload_with_wrong_token_returns_401(
    client_with_token, classic_docx_bytes
) -> None:
    resp = client_with_token.post(
        "/api/templates/upload",
        files={
            "file": ("classic.docx", classic_docx_bytes, "application/octet-stream")
        },
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Недействительный ключ администратора"}


def test_upload_with_valid_token_returns_201(
    client_with_token, classic_docx_bytes
) -> None:
    resp = client_with_token.post(
        "/api/templates/upload",
        files={
            "file": ("classic.docx", classic_docx_bytes, "application/octet-stream")
        },
        headers={"X-Admin-Token": VALID_TOKEN},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert "rules" in body


def test_empty_admin_token_blocks_upload(
    client_empty_token, classic_docx_bytes
) -> None:
    """Пустой ADMIN_TOKEN в конфиге → загрузка закрыта (401), не открыта."""
    resp = client_empty_token.post(
        "/api/templates/upload",
        files={
            "file": ("classic.docx", classic_docx_bytes, "application/octet-stream")
        },
        headers={"X-Admin-Token": "any-value-even-with-empty-config"},
    )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Недействительный ключ администратора"}


def test_list_templates_has_no_gate(client_with_token) -> None:
    """GET /api/templates работает без токена (гейт только на upload)."""
    resp = client_with_token.get("/api/templates")
    assert resp.status_code == 200
