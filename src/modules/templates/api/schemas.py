from __future__ import annotations

from pydantic import BaseModel


class TemplateItem(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    preview_url: str | None = None


class TemplateListResponse(BaseModel):
    templates: list[TemplateItem]
