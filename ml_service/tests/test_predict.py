from fastapi.testclient import TestClient
from ml_service.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_health_reports_state() -> None:
    with TestClient(app) as client:
        response = client.get("/health/model")
    assert response.status_code == 200
    assert "model_loaded" in response.json()


def test_predict_works_without_model() -> None:
    """Проверяем, что эндпоинт от тимлида работает с новой схемой."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/predict",
            json={
                "request_id": "req-1",
                "task": "processing",
                "subject_id": "u1",
                "text": "Тестовый текст",
            },
        )
    assert response.status_code == 200
    assert "predictions" in response.json()


def test_predict_is_deterministic() -> None:
    """Один и тот же запрос даёт один и тот же ответ."""
    payload = {"request_id": "req-2", "task": "processing", "text": "Тестовый текст"}
    with TestClient(app) as client:
        first = client.post("/api/v1/predict", json=payload).json()
        second = client.post("/api/v1/predict", json=payload).json()
    assert first.get("predictions") == second.get("predictions")


def test_predict_rejects_bad_schema() -> None:
    """Сломанный JSON (без request_id и text) должен падать с 422."""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/predict",
            json={"task": "invalid_task"},
        )
    assert response.status_code == 422
