from typing import Protocol

from src.modules.documents.domain.entities import Requisite


class DocxRenderer(Protocol):
    """Граница с модулем templates. Оформление применяется программно."""

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> bytes: ...
