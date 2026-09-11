"""Адаптер порта DocxRenderer из модуля documents.

TL (documents/api/router.py) импортирует TemplateDocxRenderer именно
отсюда и ожидает `render(...) -> RenderResult` (см.
documents/application/ports/docx_renderer.py): роутеру нужны не только
байты .docx, но и признак того, что сработал запасной шаблон
(contracts/api.md §4, заголовки X-Template-Fallback/-Reason).

Реальная реализация рендера живёт в infra/docx_renderer.py и отдаёт
`(bytes, Template)` через render_with_meta(). Этот класс — тонкая
прослойка, которая приводит её к контракту RenderResult и ни во что
больше не вмешивается.
"""

from __future__ import annotations

from pathlib import Path

from src.modules.documents.application.ports.docx_renderer import RenderResult
from src.modules.documents.domain.entities import Requisite
from src.modules.templates.infra.docx_renderer import (
    TemplateDocxRenderer as _InfraRenderer,
)

# Абсолютный путь к ассетам — чтобы рендер не зависел от текущей рабочей
# директории (uvicorn в контейнере стартует из /app, тесты — из корня репо).
_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


class TemplateDocxRenderer:
    """Реализация порта DocxRenderer из модуля documents."""

    def __init__(self) -> None:
        self._renderer = _InfraRenderer(assets_dir=_ASSETS_DIR)

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> RenderResult:
        content, template = self._renderer.render_with_meta(
            improved_text,
            requisites,
            template_id,
        )
        return RenderResult(
            content=content,
            template_fallback_used=template.fallback_used,
            template_fallback_reason=template.fallback_reason,
        )
