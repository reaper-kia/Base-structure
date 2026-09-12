"""Журнал обработки для GET /api/trace/{id}.

TL-13: журнал ведётся по попытке (attempt), а не по документу.
Каждый запуск пайплайна (создание или reprocess) — отдельная попытка
со своим attempt_id, таймингами, версиями и стадиями.

Эксперту должно быть видно: что ушло в ИИ, что вернулось, что решил
Fact Guard, что решил валидатор, и был ли результат взят из кэша.
In-memory достаточно.
"""

import time
from collections import defaultdict
from typing import Any
from uuid import UUID, uuid4

# document_id -> список попыток; каждая попытка — словарь с метаданными и стадиями
_ATTEMPTS: dict[UUID, list[dict[str, Any]]] = defaultdict(list)


def start_attempt(document_id: UUID, *, meta: dict[str, Any]) -> UUID:
    """Начинает новую попытку обработки и возвращает её attempt_id."""
    attempt_id = uuid4()
    _ATTEMPTS[document_id].append(
        {
            "attempt_id": str(attempt_id),
            "started_at": time.time(),
            "stages": [],
            **meta,
        }
    )
    return attempt_id


def record(
    document_id: UUID,
    attempt_id: UUID,
    stage: str,
    payload: Any,
    *,
    duration_ms: float | None = None,
) -> None:
    """Добавляет стадию в указанную попытку."""
    for attempt in _ATTEMPTS.get(document_id, []):
        if attempt["attempt_id"] == str(attempt_id):
            attempt["stages"].append(
                {
                    "stage": stage,
                    "payload": payload,
                    "duration_ms": duration_ms,
                }
            )
            return


def update_attempt_meta(
    document_id: UUID, attempt_id: UUID, **meta: Any
) -> None:
    """Обновляет метаданные попытки (например, версию модели после ответа)."""
    for attempt in _ATTEMPTS.get(document_id, []):
        if attempt["attempt_id"] == str(attempt_id):
            attempt.update(meta)
            return


def record_render(document_id: UUID, payload: Any) -> None:
    """Дописывает стадию рендера в последнюю попытку документа."""
    attempts = _ATTEMPTS.get(document_id)
    if not attempts:
        return
    attempts[-1]["stages"].append(
        {
            "stage": "render",
            "payload": payload,
            "duration_ms": None,
        }
    )


def finish_attempt(
    document_id: UUID, attempt_id: UUID, *, outcome: str
) -> None:
    """Завершает попытку: проставляет итог и общую длительность."""
    for attempt in _ATTEMPTS.get(document_id, []):
        if attempt["attempt_id"] == str(attempt_id):
            attempt["outcome"] = outcome
            finished_at = time.time()
            attempt["finished_at"] = finished_at
            attempt["total_duration_ms"] = round(
                (finished_at - attempt["started_at"]) * 1000, 2
            )
            return


def get(document_id: UUID) -> list[dict[str, Any]]:
    """Возвращает все попытки документа в хронологическом порядке."""
    return list(_ATTEMPTS.get(document_id, []))