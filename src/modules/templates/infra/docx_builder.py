from docx.oxml.ns import qn


def set_font(run, family: str) -> None:
    """Применяет шрифт ко всем 4 слотам — иначе кириллица уедет в Calibri."""
    run.font.name = family
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), family)
