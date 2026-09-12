import os
from fastapi.testclient import TestClient
from ml_service.main import app

client = TestClient(app)
DRAFTS_DIR = "tests/drafts"
FILES = [
    "01_clean.txt",
    "02_dirty.txt",
    "03_no_addressee.txt",
    "04_facts.txt",
    "05_long.txt",
]


def test_drafts_exist_and_utf8():
    """Тест 1: каждый файл из drafts/ непустой и в кодировке UTF-8"""
    for f in FILES:
        path = os.path.join(DRAFTS_DIR, f)
        assert os.path.exists(path), f"Файл {f} не найден"
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
            assert len(content.strip()) > 0, f"Файл {f} пустой"


def test_drafts_process_fallback():
    """Тест 2: прогон всех пяти через process не падает"""
    for f in FILES:
        path = os.path.join(DRAFTS_DIR, f)
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()

        payload = {
            "draft": content,
            "doc_type": "resignation",
            "doc_type_name": "Заявление",
            "structure_hint": "Деловой стиль",
            "requisite_keys": ["author"],
            "request_id": f"test-{f}",
        }
        resp = client.post("/api/v1/process", json=payload)
        # 200 OK доказывает, что сервис не упал с 500 ошибкой
        assert resp.status_code == 200
