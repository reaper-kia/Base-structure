from src.modules.documents.domain.entities import Requisite


class TemplateDocxRenderer:
    """Реализация порта DocxRenderer из модуля documents."""

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> bytes:
        raise NotImplementedError("TODO(B2)")
