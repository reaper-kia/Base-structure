from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from src.core.config import settings


async def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """Закрывает административный endpoint статическим секретом.

    Пустой ADMIN_TOKEN считается ошибкой конфигурации и оставляет endpoint
    закрытым. compare_digest не раскрывает совпавший префикс по времени ответа.
    """
    configured_token = settings.admin_token
    if (
        not configured_token
        or not x_admin_token
        or not secrets.compare_digest(x_admin_token, configured_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный ключ администратора",
        )
