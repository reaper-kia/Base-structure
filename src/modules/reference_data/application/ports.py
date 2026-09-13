from typing import Protocol

from src.modules.reference_data.domain.models import SourceHealth, Suggestion


class ReferenceDataSource(Protocol):
    """Порт чтения подсказок для реквизитов документа."""

    def suggest(self, key: str, query: str) -> list[Suggestion]: ...

    def health(self) -> SourceHealth: ...
