from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "doc3"
    app_env: str = "local"
    app_debug: bool = True

    postgres_host: str
    postgres_port: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://redis:6379/0"
    redis_key_prefix: str = "doc3"

    # Кэш результатов ИИ-обработки по хэшу черновика.
    cache_ttl_seconds: int = 600

    kafka_bootstrap_servers: str = "kafka:9093"
    kafka_client_id: str = "app"
    kafka_events_consumer_group: str = "app.events"
    kafka_events_topic: str = "app.events.v1"
    kafka_events_dlq_topic: str = "app.events.dlq.v1"
    kafka_consumer_max_attempts: int = 3
    kafka_consumer_retry_delay_seconds: float = 1.0
    outbox_publisher_batch_size: int = 100
    outbox_publisher_poll_interval_seconds: float = 1.0

    # Пустая строка = ИИ отключён. Бэкенд обязан пережить это (сценарий 6).
    ml_service_url: str = "http://ml_service:8100"
    ml_request_timeout_seconds: float = 90.0

    # Тумблер для демонстрации отказа ИИ.
    ai_force_failure: bool = False

    templates_dir: str = "src/modules/templates/assets"
    default_template_id: str = "classic"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()  # type: ignore[call-arg]
