from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ML Service"
    app_debug: bool = False

    # Куда обучающий скрипт кладёт артефакт и откуда сервис его читает.
    # Если файла нет - сервис ВСЁ РАВНО стартует и работает на заглушке.
    model_path: Path = Path("artifacts/model.joblib")

    # Выключай только если хочешь явно увидеть 503 вместо тихой заглушки.
    # На демо всегда должно быть True.
    fallback_enabled: bool = True

    # Ограничение времени на один инференс. Если модель думает дольше -
    # отдаём заглушку. Демо не должно висеть.
    predict_timeout_seconds: float = 2.0

    # LLM (Ollama) для /api/v1/process. В docker-сети хост НЕ localhost, а имя
    # сервиса `ollama` — раньше адрес был захардкожен в main.py на localhost,
    # из-за чего в собранном стеке сервис никогда не доходил до модели и всегда
    # молча возвращал исходный текст (fallback). Значения берём из окружения
    # (docker-compose уже прокидывает OLLAMA_URL / OLLAMA_MODEL).
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout_seconds: float = 90.0

    host: str = "0.0.0.0"
    port: int = 8100


settings = Settings()
