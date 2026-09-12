from __future__ import annotations

from pydantic import BaseModel


class TemplateItem(BaseModel):
    id: str
    name: str
    description: str
    available: bool


class TemplateListResponse(BaseModel):
    templates: list[TemplateItem]
