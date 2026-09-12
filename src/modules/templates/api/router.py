from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import redis.asyncio as aioredis
import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.core.config import settings
from src.modules.templates.api.dependencies import require_admin_token
from src.modules.templates.api.schemas import TemplateItem, TemplateListResponse
from src.modules.templates.application.template_service import (
    DEFAULT_ASSETS_DIR,
    TemplateLoader,
)
from src.modules.templates.infra.docx_parser import NotADocxError, parse_docx_template

ASSETS_DIR = DEFAULT_ASSETS_DIR  # вшитые шаблоны (остаются в образе)
UPLOADED_DIR = Path(settings.uploaded_templates_dir)  # каталог загрузок (B2-14)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # п. 7.4: больше 10 МБ → 413
VERSION_KEY = "templates:version"

_redis_client: aioredis.Redis | None = None

router = APIRouter()
_loader = TemplateLoader(uploaded_dir=UPLOADED_DIR)


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _preview_url(template_id: str) -> str | None:
    """B2-13.5: не шлём preview_url, если файла нет (фронт покажет заглушку)."""
    candidates = (
        Path("src/static/templates") / f"{template_id}.png",
        ASSETS_DIR / f"{template_id}.png",
        UPLOADED_DIR / template_id / "preview.png",
    )
    if any(candidate.exists() for candidate in candidates):
        return f"/static/templates/{template_id}.png"
    return None


@router.get(
    "/api/templates",
    response_model=TemplateListResponse,
    summary="Справочник шаблонов оформления",
)
async def list_templates() -> TemplateListResponse:
    templates = _loader.list_templates()
    items = [
        TemplateItem(
            id=t.id,
            name=t.name,
            description=t.description,
            available=t.available,
            preview_url=_preview_url(t.id),
        )
        for t in templates
    ]
    return TemplateListResponse(templates=items)


@router.get(
    "/api/templates/version",
    summary="Счётчик версий справочника шаблонов",
)
async def get_templates_version() -> dict[str, int]:
    """Версия растёт на 1 на каждую успешную загрузку (B2-14.2, Redis INCR)."""
    raw = await _get_redis().get(VERSION_KEY)
    return {"version": int(raw) if raw else 0}


@router.post(
    "/api/templates/upload",
    status_code=201,
    summary="Загрузка и автопарсинг DOCX-шаблона",
)
async def upload_template(
    file: Annotated[UploadFile, File(...)],
    _admin: None = Depends(require_admin_token),
):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 10 МБ")
    try:
        rules, warnings = parse_docx_template(data)
    except NotADocxError:
        raise HTTPException(
            status_code=422, detail="Файл не является корректным DOCX"
        ) from None
    base = (
        re.sub(r"[^a-z0-9]+", "-", (file.filename or "template").lower()).strip("-")
        or "template"
    )
    template_id, counter = base, 1
    while (ASSETS_DIR / template_id).exists() or (UPLOADED_DIR / template_id).exists():
        template_id = f"{base}-{counter}"
        counter += 1
    folder = UPLOADED_DIR / template_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "template.docx").write_bytes(data)
    (folder / "rules.yaml").write_text(
        yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    await _get_redis().incr(VERSION_KEY)
    return {
        "id": template_id,
        "name": rules["name"],
        "rules": rules,
        "warnings": warnings,
    }