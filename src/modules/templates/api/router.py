from __future__ import annotations

from fastapi import APIRouter

from src.modules.templates.application.template_service import TemplateLoader
from src.modules.templates.api.schemas import TemplateItem, TemplateListResponse

router = APIRouter()

_loader = TemplateLoader()


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
            preview_url=f"/static/templates/{t.id}.png",
        )
        for t in templates
    ]

    return TemplateListResponse(templates=items)

import re
import yaml
from fastapi import File, HTTPException, UploadFile
from src.modules.templates.application.template_service import DEFAULT_ASSETS_DIR
from src.modules.templates.infra.docx_parser import NotADocxError, parse_docx_template

ASSETS_DIR = DEFAULT_ASSETS_DIR          # подменяется в тестах
MAX_UPLOAD_BYTES = 10 * 1024 * 1024      # п. 7.4: больше 10 МБ → 413


@router.post("/api/templates/upload", status_code=201, summary="Загрузка и автопарсинг DOCX-шаблона")
async def upload_template(file: UploadFile = File(...)):
    data = await file.read()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 10 МБ")

    try:
        rules, warnings = parse_docx_template(data)
    except NotADocxError:
        raise HTTPException(status_code=422, detail="Файл не является корректным DOCX")

    base = re.sub(r"[^a-z0-9]+", "-", (file.filename or "template").lower()).strip("-") or "template"
    template_id, counter = base, 1
    while (ASSETS_DIR / template_id).exists():
        template_id = f"{base}-{counter}"
        counter += 1

    folder = ASSETS_DIR / template_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "template.docx").write_bytes(data)
    (folder / "rules.yaml").write_text(
        yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    return {"id": template_id, "name": rules["name"], "rules": rules, "warnings": warnings}