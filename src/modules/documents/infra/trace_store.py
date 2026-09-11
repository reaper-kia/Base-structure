"""Журнал обработки для GET /api/trace/{id}.

Эксперту должно быть видно: что ушло в ИИ, что вернулось, что решил
Fact Guard, что решил валидатор. In-memory достаточно.
"""

from collections import defaultdict
from typing import Any
from uuid import UUID

_TRACES: dict[UUID, list[dict[str, Any]]] = defaultdict(list)


def record(document_id: UUID, stage: str, payload: Any) -> None:
    _TRACES[document_id].append({"stage": stage, "payload": payload})


def get(document_id: UUID) -> list[dict[str, Any]]:
    return _TRACES.get(document_id, [])
