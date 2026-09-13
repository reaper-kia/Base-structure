from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.modules.reference_data.api.dependencies import get_reference_source
from src.modules.reference_data.domain.models import (
    SourceHealth,
    SourceStatus,
    Suggestion,
)
from src.modules.reference_data.infra.null_source import NullReferenceSource


class FakeReferenceSource:
    def suggest(self, key: str, query: str) -> list[Suggestion]:
        assert key == "addressee"
        assert query == "Иван"
        return [
            Suggestion(
                key=key,
                value="Иванов Иван Иванович",
                source="Корпоративный справочник",
                document="Карточка сотрудника № 42",
                source_date=date(2026, 9, 1),
            )
        ]

    def health(self) -> SourceHealth:
        return SourceHealth(status=SourceStatus.OK, message="Источник доступен")


@pytest.mark.api
def test_suggestion_exposes_provenance_and_requires_confirmation() -> None:
    app.dependency_overrides[get_reference_source] = lambda: FakeReferenceSource()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/reference-data/suggestions",
                params={"key": "addressee", "query": "Иван"},
            )
    finally:
        app.dependency_overrides.pop(get_reference_source, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_user_confirmation"] is True
    assert payload["suggestions"] == [
        {
            "key": "addressee",
            "value": "Иванов Иван Иванович",
            "source": "Корпоративный справочник",
            "document": "Карточка сотрудника № 42",
            "date": "2026-09-01",
        }
    ]


@pytest.mark.api
def test_unconfigured_source_degrades_without_error() -> None:
    app.dependency_overrides[get_reference_source] = lambda: NullReferenceSource()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/reference-data/suggestions",
                params={"key": "addressee", "query": "Иван"},
            )
    finally:
        app.dependency_overrides.pop(get_reference_source, None)

    assert response.status_code == 200
    assert response.json()["health"]["status"] == "not_configured"
    assert response.json()["suggestions"] == []
