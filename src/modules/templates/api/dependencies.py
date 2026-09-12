from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from src.core.config import settings


async def require_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный ключ администратора",
        )
    if not x_admin_token or not secrets.compare_digest(
        x_admin_token, settings.admin_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный ключ администратора",
        )
