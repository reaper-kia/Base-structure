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
    # Короткий ТТЛ для кэша резервных (неуспешных) результатов.
    fallback_cache_ttl_seconds: int = 30

    # Версия промпта/схемы. Используется в ключе кэша для инвалидации
    # при обновлении модели или промпта.
    prompt_version: str = "1.2.0"

    # Максимальное время обработки документа (дедлайн).
    processing_deadline_seconds: int = 180

    # Пустая строка = ИИ отключён. Бэкенд обязан пережить это (сценарий 6).
    ml_service_url: str = "http://ml_service:8100"
    ml_request_timeout_seconds: float = 90.0

    # Тумблер для демонстрации отказа ИИ.
    ai_force_failure: bool = False

    templates_dir: str = "src/modules/templates/assets"
    default_template_id: str = "classic"

    # Шаблоны, загруженные пользователем. Отдельный каталог, потому что
    # прод-контейнер поднят с read_only: true — писать в образ нельзя,
    # а этот путь монтируется томом (см. compose.prod.yml).
    user_templates_dir: str = "data/templates"

    # Секрет для административных операций. Пустое значение закрывает
    # загрузку шаблонов (fail closed), а не отключает проверку.
    admin_token: str = ""

    # Необязательная точка подключения корпоративного справочника/СЭД.
    # Пустое значение означает, что источник не настроен; основной путь
    # создания документов от этого не зависит.
    reference_source_url: str = ""

    # Название организации в верхнем колонтитуле шаблона «Классический
    # корпоративный» (организаторы: «Верхний — название организации»).
    # Значение по умолчанию — плейсхолдер из эталонного шаблона: своё
    # название сервис не выдумывает, его подставляет владелец стенда.
    org_name: str = "[Название организации]"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()  # type: ignore[call-arg]
