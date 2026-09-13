from fastapi.testclient import TestClient
from ml_service.main import app

def test_stt_invalid_format():
    """Тест: файл неверного формата дает 422, а не 500 (критерий ML-11.7)."""
    # Использование 'with' запускает lifespan (в том числе load_stt_model)
    with TestClient(app) as client:
        files = {"audio": ("test.mp3", b"not_a_real_audio_data", "audio/mpeg")}
        resp = client.post("/stt", files=files)
        assert resp.status_code == 422
        assert "invalid_format" in resp.json()["detail"]
