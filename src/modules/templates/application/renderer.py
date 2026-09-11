from src.modules.documents.application.ports.docx_renderer import RenderResult
from src.modules.documents.domain.entities import Requisite


class TemplateDocxRenderer:
    """Реализация порта DocxRenderer из модуля documents.

    TL-07: сигнатура поменялась с `-> bytes` на `-> RenderResult` (см.
    application/ports/docx_renderer.py) - роутеру нужно знать не только сами
    байты .docx, но и сработал ли запасной шаблон (contracts/api.md §4,
    заголовки X-Template-Fallback/-Reason). Внутри реализации: если
    template_loader.load(template_id) вернул Template с fallback_used=True -
    прокинь это поле и причину сюда, в RenderResult.
    """

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> RenderResult:
        raise NotImplementedError("TODO(B2)")
