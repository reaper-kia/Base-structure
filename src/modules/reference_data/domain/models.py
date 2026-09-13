from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SourceStatus(StrEnum):
    OK = "ok"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SourceHealth:
    status: SourceStatus
    message: str


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Значение реквизита вместе с обязательным происхождением."""

    key: str
    value: str
    source: str
    document: str
    source_date: date

    def __post_init__(self) -> None:
        required = {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "document": self.document,
        }
        if any(not value.strip() for value in required.values()):
            raise ValueError("Подсказка обязана содержать значение и происхождение")
