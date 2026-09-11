"""Программное оформление DOCX по правилам шаблона.

ИИ сюда не заглядывает: он отдал текст и реквизиты, дальше всё решает код.
"""

from docx.oxml.ns import qn
from docx.text.run import Run


def set_font(run: Run, family: str) -> None:
    """Кириллица в Word ломается, если шрифт прописан не во всех четырёх слотах."""
    run.font.name = family
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), family)


def build(improved_text: str, requisites: list, rules: dict) -> bytes:
    raise NotImplementedError("TODO(B2)")
