"""Изоляция имитации отказа ИИ по демонстрационной сессии (TL-14).

Каждый эксперт получает собственную сессию через cookie `dev_session`.
Включённый одним экспертом тумблер «Имитировать отказ ИИ» не влияет на
документы других экспертов.

Храним в памяти: для демонстрации этого достаточно. При рестарте сервиса
сессии сбрасываются (тумблер выключается), что приемлемо.
"""

import uuid
from typing import Any

COOKIE_NAME = "dev_session"

# session_id -> {"ai_force_failure": bool}
_SESSIONS: dict[str, dict[str, Any]] = {}


def resolve_session_id(cookie_value: str | None) -> tuple[str, bool]:
    """Определяет идентификатор сессии.

    Возвращает (session_id, is_new). Если cookie пустой или отсутствует,
    генерируется новый идентификатор.
    """
    if cookie_value:
        return cookie_value, False
    return uuid.uuid4().hex, True


def get_ai_force_failure(session_id: str) -> bool:
    """Возвращает флаг имитации отказа для сессии (по умолчанию False)."""
    session = _SESSIONS.get(session_id)
    if session is None:
        return False
    return bool(session.get("ai_force_failure", False))


def set_ai_force_failure(session_id: str, enabled: bool) -> None:
    """Устанавливает флаг имитации отказа для сессии."""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {}
    _SESSIONS[session_id]["ai_force_failure"] = enabled
