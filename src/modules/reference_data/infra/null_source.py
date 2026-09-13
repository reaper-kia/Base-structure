from src.core.config import settings
from src.modules.reference_data.domain.models import (
    SourceHealth,
    SourceStatus,
    Suggestion,
)


class NullReferenceSource:
    """Безопасная заглушка: никогда не выдумывает внешние данные."""

    def __init__(self, configured_url: str = "") -> None:
        self._configured_url = configured_url.strip()

    @classmethod
    def from_settings(cls) -> "NullReferenceSource":
        return cls(settings.reference_source_url)

    def suggest(self, key: str, query: str) -> list[Suggestion]:
        # Даже при случайно заданном URL заглушка не делает сетевых запросов
        # и не подставляет данные вместо настоящего адаптера.
        del key, query
        return []

    def health(self) -> SourceHealth:
        if not self._configured_url:
            return SourceHealth(
                status=SourceStatus.NOT_CONFIGURED,
                message="Источник справочных данных не настроен",
            )
        return SourceHealth(
            status=SourceStatus.UNAVAILABLE,
            message=("Адрес источника задан, но адаптер подключения не установлен"),
        )
