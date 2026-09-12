"""Общая настройка тестов ml_service.

Тесты не ходят в реальную Ollama: адрес принудительно уводится в
заведомо закрытый порт, чтобы соединение отвергалось сразу, а не висело
до таймаута. Это же делает поведение детерминированным — любой прогон
идёт по ветке fallback, если тест сам не подменил клиента.
"""

import pytest

from ml_service.config import settings


@pytest.fixture(autouse=True)
def offline_ollama():
    original_url = settings.ollama_url
    original_timeout = settings.ollama_timeout_seconds
    original_health_timeout = settings.ollama_health_timeout_seconds

    settings.ollama_url = "http://127.0.0.1:1"
    settings.ollama_timeout_seconds = 1.0
    settings.ollama_health_timeout_seconds = 1.0

    yield

    settings.ollama_url = original_url
    settings.ollama_timeout_seconds = original_timeout
    settings.ollama_health_timeout_seconds = original_health_timeout
