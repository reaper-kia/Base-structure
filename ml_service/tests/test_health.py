from fastapi.testclient import TestClient

from ml_service.config import settings
from ml_service.main import app

client = TestClient(app)


def test_health_is_always_ok_even_without_model() -> None:
    """§2: /health отвечает 200 и без модели.

    Иначе Docker перезапускает контейнер, который работоспособен
    в режиме деградации.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_health_reports_unavailable_model_with_reason() -> None:
    """Без Ollama сервис честно сообщает, что модели нет, и объясняет почему."""
    response = client.get("/health/model")
    payload = response.json()

    assert response.status_code == 200
    assert payload["model_loaded"] is False
    assert payload["fallback_enabled"] is True
    assert payload["supported_tasks"] == ["process"]
    assert payload["detail"]


def test_rag_health_reports_disabled_mode() -> None:
    response = client.get("/health/rag")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "state": "disabled",
        "embedding_model": "bge-m3",
        "knowledge_files": 0,
        "indexed_chunks": 0,
        "vector_available": False,
        "last_method": None,
        "last_error": None,
    }


def test_rag_health_indexes_bundled_knowledge_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_enabled", True)

    response = client.get("/health/rag")
    payload = response.json()

    assert response.status_code == 200
    assert payload["enabled"] is True
    assert payload["state"] in {"empty", "ready"}
    assert payload["last_error"] is None
