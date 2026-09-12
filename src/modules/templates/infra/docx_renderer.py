from __future__ import annotations

import hashlib
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus
from src.modules.templates.application.template_service import TemplateLoader
from src.modules.templates.domain.entities import Template
from src.modules.templates.infra.docx_builder import set_font


def _clear_paragraphs(element) -> None:
    """Физически удаляет все параграфы из элемента (тело, колонтитул, ячейка)."""
    for p in list(element.paragraphs):
        p._element.getparent().remove(p._element)


def _clear_tables(element) -> None:
    """Удаляет таблицы тела документа (остатки образца, двойная шапка modern)."""
    for table in list(element.tables):
        table._element.getparent().remove(table._element)


def _safe_format(template: str, **kwargs) -> str:
    """Безопасная подстановка: неизвестные ключи дают пустую строку, а не [ключ]."""

    class _DefaultDict(defaultdict):
        def __missing__(self, key):
            return ""

    return template.format_map(_DefaultDict(str, kwargs))


def _append_page_field(run) -> None:
    """Добавляет в run настоящее поле PAGE: Word подставит номер страницы сам."""
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._element.append(begin)
    run._element.append(instr)
    run._element.append(end)


class TemplateDocxRenderer:
    """Реализация порта DocxRenderer: тимлид вызывает render() и только её."""

    def __init__(self, assets_dir: Path | str = "src/modules/templates/assets") -> None:
        self.loader = TemplateLoader(assets_dir)
        # Кэш готовых рендеров: (отпечаток текста, реквизиты, шаблон) -> байты DOCX
        self._revision_cache: dict[tuple[str, tuple, str], bytes] = {}

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> bytes:
        data, _ = self.render_with_meta(improved_text, requisites, template_id)
        return data

    def render_with_meta(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> tuple[bytes, Template]:
        """Рендер + метаданные шаблона (нужны для X-Template-Fallback)."""
        template = self.loader.load_with_fallback(template_id)
        rules = template.rules

        doc = Document(template.docx_path) if template.docx_path else Document()
        _clear_paragraphs(doc)
        _clear_tables(doc)

        self._apply_page_settings(doc, rules)
        self._apply_headers_footers(doc, rules, requisites)
        self._apply_layout(doc, rules, requisites, improved_text)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue(), template

    def render_from_revision(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> tuple[bytes, Template]:
        """Рендер из неизменной ревизии (B2-07): LLM не вызывается, меняется только шаблон.

        Кэш по (отпечаток текста, реквизиты, шаблон): повторный запрос того же
        содержания в том же шаблоне отдаёт готовый DOCX из памяти.
        Смена шаблона = новый ключ кэша = пересборка оформления без модели.
        """
        cache_key = (
            hashlib.sha256(improved_text.encode("utf-8")).hexdigest(),
            tuple((r.key, r.value, str(r.status)) for r in requisites),
            template_id,
        )

        if cache_key not in self._revision_cache:
            data, _ = self.render_with_meta(improved_text, requisites, template_id)
            self._revision_cache[cache_key] = data

        template = self.loader.load_with_fallback(template_id)
        return self._revision_cache[cache_key], template

    def _apply_page_settings(self, doc: Document, rules: dict) -> None:
        section = doc.sections[0]
        page = rules["page"]
        section.top_margin = Mm(page["top_mm"])
        section.bottom_margin = Mm(page["bottom_mm"])
        section.left_margin = Mm(page["left_mm"])
        section.right_margin = Mm(page["right_mm"])

    def _apply_headers_footers(
        self, doc: Document, rules: dict, requisites: list[Requisite]
    ) -> None:
        hf = rules.get("header_footer", {})
        section = doc.sections[0]
        context = {r.key: (r.value or "") for r in requisites}

        # ВСЕГДА вычищаем остатки образца из колонтитулов,
        # даже если правила не задают текст (иначе выживает серый плейсхолдер).
        _clear_paragraphs(section.header)
        _clear_paragraphs(section.footer)

        header_cfg = hf.get("header", {})
        if header_cfg.get("text"):
            para = section.header.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._render_text_with_page_field(
                para,
                header_cfg["text"],
                context,
                header_cfg.get("font_family", rules["font"]["family"]),
                header_cfg.get("font_size_pt", rules["font"]["size_pt"] - 3),
            )

        footer_cfg = hf.get("footer", {})
        if footer_cfg.get("text"):
            para = section.footer.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self._render_text_with_page_field(
                para,
                footer_cfg["text"],
                context,
                footer_cfg.get("font_family", rules["font"]["family"]),
                footer_cfg.get("font_size_pt", rules["font"]["size_pt"] - 3),
            )

    def _render_text_with_page_field(
        self,
        para,
        text: str,
        context: dict,
        family: str,
        size_pt: float,
    ) -> None:
        """Собирает текст колонтитула; токен {page} становится полем PAGE."""
        parts = text.split("{page}")
        for i, part in enumerate(parts):
            rendered = _safe_format(part, **context)
            if rendered:
                run = para.add_run(rendered)
                set_font(run, family)
                run.font.size = Pt(size_pt)
            if i < len(parts) - 1:
                field_run = para.add_run()
                set_font(field_run, family)
                field_run.font.size = Pt(size_pt)
                _append_page_field(field_run)

    def _apply_layout(
        self,
        doc: Document,
        rules: dict,
        requisites: list[Requisite],
        improved_text: str,
    ) -> None:
        font_family = rules["font"]["family"]
        font_size = rules["font"]["size_pt"]
        spacing = rules.get("spacing", {})

        alignment_map = {
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "both": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "top_left": WD_ALIGN_PARAGRAPH.LEFT,
            "top_right": WD_ALIGN_PARAGRAPH.RIGHT,
            "bottom_center": WD_ALIGN_PARAGRAPH.CENTER,
            "bottom_left": WD_ALIGN_PARAGRAPH.LEFT,
            "bottom_right": WD_ALIGN_PARAGRAPH.RIGHT,
        }

        for block in rules["requisites_layout"]:
            key = block["key"]

            if key == "body":
                self._add_body_text(
                    doc,
                    improved_text,
                    rules,
                    font_family,
                    font_size,
                    spacing,
                    alignment_map,
                )
                continue

            if block.get("type") == "table" or block.get("layout") == "table":
                self._render_table_block(doc, block, requisites, font_family, font_size)
                continue

            req = next((r for r in requisites if r.key == key), None)

            # Необязательный реквизит без значения не рендерится вовсе
            if req is None or (not req.required and not req.value):
                continue

            is_missing = (
                not req.value
                or req.status == RequisiteStatus.MISSING
                or req.status == "left_blank"
            )

            para = doc.add_paragraph()
            para.alignment = alignment_map.get(
                block.get("position", "left"), WD_ALIGN_PARAGRAPH.LEFT
            )

            if is_missing:
                run = para.add_run(f"[{req.label}]")
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            else:
                run = para.add_run(req.value)

            set_font(run, font_family)
            run.font.size = Pt(font_size)
            if block.get("bold"):
                run.bold = True

    def _render_table_block(
        self,
        doc: Document,
        block: dict,
        requisites: list[Requisite],
        font_family: str,
        font_size: float,
    ) -> None:
        """Рендерит табличный блок (например, «Кому / От кого» в modern)."""
        rows_cfg = block.get("rows", [])
        if not rows_cfg:
            return

        table = doc.add_table(rows=len(rows_cfg), cols=2)
        table.autofit = True

        for i, row_cfg in enumerate(rows_cfg):
            label = str(row_cfg.get("label", ""))
            value_key = str(row_cfg.get("value_key", ""))

            req = next((r for r in requisites if r.key == value_key), None)

            if req is None:
                value, apply_highlight = "", False
            elif not req.required and not req.value:
                value, apply_highlight = "", False
            elif (
                not req.value
                or req.status == RequisiteStatus.MISSING
                or req.status == "left_blank"
            ):
                value = f"[{req.label}]"
                apply_highlight = True
            else:
                value = str(req.value)
                apply_highlight = False

            cell_label = table.cell(i, 0)
            _clear_paragraphs(cell_label)
            run_label = cell_label.add_paragraph().add_run(label)
            set_font(run_label, font_family)
            run_label.font.size = Pt(font_size)
            run_label.bold = True

            cell_value = table.cell(i, 1)
            _clear_paragraphs(cell_value)
            if value:
                run_value = cell_value.add_paragraph().add_run(value)
                set_font(run_value, font_family)
                run_value.font.size = Pt(font_size)
                if apply_highlight:
                    run_value.font.highlight_color = WD_COLOR_INDEX.YELLOW
            else:
                cell_value.add_paragraph()

    def _add_body_text(
        self,
        doc: Document,
        text: str,
        rules: dict,
        font_family: str,
        font_size: float,
        spacing: dict,
        alignment_map: dict,
    ) -> None:
        # Выравнивание берём из правил, а не хардкодом (classic: justify, modern: left)
        align = alignment_map.get(
            rules.get("alignment", "justify"), WD_ALIGN_PARAGRAPH.JUSTIFY
        )

        for para_text in text.split("\n\n"):
            if not para_text.strip():
                continue

            para = doc.add_paragraph()
            para.alignment = align

            if "line" in spacing:
                para.paragraph_format.line_spacing = spacing["line"]
            if "first_line_indent_cm" in spacing:
                para.paragraph_format.first_line_indent = Cm(
                    spacing["first_line_indent_cm"]
                )
            if "space_after_pt" in spacing:
                para.paragraph_format.space_after = Pt(spacing["space_after_pt"])

            run = para.add_run(para_text.strip())
            set_font(run, font_family)
            run.font.size = Pt(font_size)
