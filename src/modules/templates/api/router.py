"""Справочник шаблонов оформления и загрузка своего DOCX.

Загрузка произвольного шаблона — расширение сверх обязательного минимума
(задание, п. 1.6: «автоматический разбор произвольного загруженного
DOCX-шаблона не является обязательным требованием, но будет существенным
дополнительным преимуществом»).
"""

from __future__ import annotations

import re
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.modules.templates.api.dependencies import require_admin_token
from src.modules.templates.api.schemas import TemplateItem, TemplateListResponse
from src.modules.templates.application.template_service import (
    TemplateLoader,
    user_templates_dir,
)
from src.modules.templates.infra.docx_parser import NotADocxError, parse_docx_template

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter()

_loader = TemplateLoader()


@router.get(
    "/api/templates",
    response_model=TemplateListResponse,
    summary="Справочник шаблонов оформления",
)
async def list_templates() -> TemplateListResponse:
    return TemplateListResponse(
        templates=[
            TemplateItem(
                id=template.id,
                name=template.name,
                description=template.description,
                available=template.available,
            )
            for template in _loader.list_templates()
        ]
    )


@router.post(
    "/api/templates/upload",
    status_code=201,
    summary="Загрузка и автоматический разбор DOCX-шаблона",
)
async def upload_template(
    file: Annotated[UploadFile, File(...)],
    _admin: None = Depends(require_admin_token),
) -> dict:
    data = await file.read()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 10 МБ")

    try:
        rules, warnings = parse_docx_template(data)
    except NotADocxError:
        raise HTTPException(
            status_code=422, detail="Файл не является корректным DOCX"
        ) from None

    # Каталог пользовательских шаблонов монтируется томом: образ приложения
    # поднят с read_only: true, писать в assets нельзя.
    target_dir = user_templates_dir()

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Каталог пользовательских шаблонов недоступен для записи. "
                "Проверьте том USER_TEMPLATES_DIR."
            ),
        ) from exc

    base = (
        re.sub(r"[^a-z0-9]+", "-", (file.filename or "template").lower()).strip("-")
        or "template"
    )
    # Имя встроенного шаблона занять нельзя: иначе загрузкой файла можно
    # было бы подменить classic для всех пользователей.
    reserved = {template.id for template in _loader.list_templates()}

    template_id, counter = base, 1
    while template_id in reserved or (target_dir / template_id).exists():
        template_id = f"{base}-{counter}"
        counter += 1

    folder = target_dir / template_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "template.docx").write_bytes(data)
    (folder / "rules.yaml").write_text(
        yaml.safe_dump(rules, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    return {
        "id": template_id,
        "name": rules["name"],
        "rules": rules,
        "warnings": warnings,
    }
