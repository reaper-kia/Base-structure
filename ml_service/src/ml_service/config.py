"""Настройки ml_service.

Сервис сознательно не знает ничего про типы документов: всё, что нужно для
промпта (название типа, подсказка по структуре, список ключей реквизитов),
приходит в запросе от бэкенда — contracts/llm_contract.md §2.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ML Service"
    app_debug: bool = False

    # Ollama. В docker-сети хост не localhost, а имя сервиса.
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout_seconds: float = 90.0
    # Короткий таймаут для проверок доступности (GET /api/tags).
    ollama_health_timeout_seconds: float = 3.0

    # Температура выше 0.2 — модель начинает «улучшать» факты
    # (contracts/llm_contract.md §3.1).
    ollama_temperature: float = 0.2

    # Сколько раз повторяем основной вызов модели при невалидном ответе
    # (contracts/llm_contract.md §3.2).
    max_attempts: int = 2

    # Repair-проход: второй вызов модели «почини этот JSON»
    # (contracts/llm_contract.md §4, шаг 2).
    repair_enabled: bool = True

    # Выключай только если хочешь увидеть 503 вместо rule-based fallback.
    # На демо всегда True (contracts/llm_contract.md §2).
    fallback_enabled: bool = True

    host: str = "0.0.0.0"
    port: int = 8100


settings = Settings()
