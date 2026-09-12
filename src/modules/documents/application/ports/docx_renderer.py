from dataclasses import dataclass
from typing import Protocol

from src.modules.documents.domain.entities import Requisite


@dataclass
class RenderResult:
    """TL-07: одного bytes недостаточно - нужно ещё знать про fallback.

    contracts/template_format.md §2.7: при повреждённом шаблоне рендерер не
    падает, тихо подставляет settings.default_template_id и сообщает об
    этом наверх - иначе api/router.py не сможет выставить заголовки
    X-Template-Fallback/-Reason из contracts/api.md §4.
    """

    content: bytes
    template_fallback_used: bool = False
    template_fallback_reason: str | None = None


class DocxRenderer(Protocol):
    """Граница с модулем templates. Оформление применяется программно."""

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
        doc_type_name: str = "",
    ) -> RenderResult:
        """doc_type_name печатается заголовком («СЛУЖЕБНАЯ ЗАПИСКА»).

        Пустая строка = тип документа не просит печатать своё название:
        письмо в эталонных примерах организаторов начинается сразу с темы.
        """
        ...
