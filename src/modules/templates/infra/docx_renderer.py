from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.shared import Cm, Mm, Pt

from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus
from src.modules.templates.application.template_service import TemplateLoader
from src.modules.templates.domain.entities import Template
from src.modules.templates.infra.docx_builder import set_font


def _clear_paragraphs(element) -> None:
    """Физически удаляет все параграфы из элемента."""
    for p in list(element.paragraphs):
        p._element.getparent().remove(p._element)


def _safe_format(template: str, **kwargs) -> str:
    """Безопасный format: неизвестные ключи заменяются на "[key]". """
    class _DefaultDict(defaultdict):
        def __missing__(self, key):
            return f"[{key}]"
    
    return template.format_map(_DefaultDict(str, kwargs))


class TemplateDocxRenderer:
    def __init__(self, assets_dir: Path | str = "src/modules/templates/assets"):
        self.loader = TemplateLoader(assets_dir)

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
        """Рендер + информация о шаблоне (нужна для X-Template-Fallback)."""
        template = self.loader.load_with_fallback(template_id)
        rules = template.rules

        doc = Document(template.docx_path) if template.docx_path else Document()
        _clear_paragraphs(doc)

        self._apply_page_settings(doc, rules)
        self._apply_headers_footers(doc, rules, requisites)
        self._apply_layout(doc, rules, requisites, improved_text)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue(), template

    def _apply_page_settings(self, doc: Document, rules: dict) -> None:
        section = doc.sections[0]
        page = rules["page"]
        section.top_margin = Mm(page["top_mm"])
        section.bottom_margin = Mm(page["bottom_mm"])
        section.left_margin = Mm(page["left_mm"])
        section.right_margin = Mm(page["right_mm"])

    def _apply_headers_footers(self, doc: Document, rules: dict, requisites: list[Requisite]) -> None:
        hf = rules.get("header_footer", {})
        section = doc.sections[0]
        
        context = {r.key: (r.value or "") for r in requisites}
        
        header_cfg = hf.get("header", {})
        header_text = header_cfg.get("text", "")
        if header_text:
            header_text = _safe_format(header_text, **context)
            _clear_paragraphs(section.header)
            para = section.header.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(header_text)
            set_font(run, header_cfg.get("font_family", rules["font"]["family"]))
            run.font.size = Pt(header_cfg.get("font_size_pt", rules["font"]["size_pt"] - 3))

        footer_cfg = hf.get("footer", {})
        footer_text = footer_cfg.get("text", "")
        if footer_text:
            footer_text = _safe_format(footer_text, **context)
            _clear_paragraphs(section.footer)
            para = section.footer.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(footer_text)
            set_font(run, footer_cfg.get("font_family", rules["font"]["family"]))
            run.font.size = Pt(footer_cfg.get("font_size_pt", rules["font"]["size_pt"] - 3))

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
                self._add_body_text(doc, improved_text, font_family, font_size, spacing, alignment_map)
                continue

            if block.get("type") == "table" or block.get("layout") == "table":
                self._render_table_block(doc, block, requisites, font_family, font_size)
                continue

            req = next((r for r in requisites if r.key == key), None)

            # ТЗ 5.3: Необязательный реквизит без значения не рендерится вовсе
            if req is None or (not req.required and not req.value):
                continue

            # ТЗ 5.1: Реквизит со статусом missing или left_blank (или без значения для обязательного)
            is_missing = (
                not req.value or 
                req.status == RequisiteStatus.MISSING or 
                req.status == "left_blank"
            )

            para = doc.add_paragraph()
            pos = block.get("position", "left")
            para.alignment = alignment_map.get(pos, WD_ALIGN_PARAGRAPH.LEFT)

            if is_missing:
                text_to_add = f"[{req.label}]"
                run = para.add_run(text_to_add)
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            else:
                text_to_add = req.value
                run = para.add_run(text_to_add)

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
        rows_cfg = block.get("rows", [])
        if not rows_cfg:
            return

        table = doc.add_table(rows=len(rows_cfg), cols=2)
        table.autofit = True
        
        for i, row_cfg in enumerate(rows_cfg):
            label = str(row_cfg.get("label", ""))
            value_key = str(row_cfg.get("value_key", ""))
            
            req = next((r for r in requisites if r.key == value_key), None)
            
            # ТЗ 5.3: Необязательный без значения не рендерится (в таблице оставляем пустым)
            is_optional_empty = req and not req.required and not req.value
            
            is_missing = (
                req is None or 
                not req.value or 
                req.status == RequisiteStatus.MISSING or 
                req.status == "left_blank"
            )

            if is_optional_empty:
                value = ""
                apply_highlight = False
            elif is_missing:
                value = f"[{req.label if req else value_key}]"
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
            run_value = cell_value.add_paragraph().add_run(value)
            set_font(run_value, font_family)
            run_value.font.size = Pt(font_size)
            
            if apply_highlight:
                run_value.font.highlight_color = WD_COLOR_INDEX.YELLOW

    def _add_body_text(
        self,
        doc: Document,
        text: str,
        font_family: str,
        font_size: float,
        spacing: dict,
        alignment_map: dict,
    ) -> None:
        align = alignment_map.get("justify", WD_ALIGN_PARAGRAPH.JUSTIFY)
        paragraphs = text.split("\n\n")
        
        for para_text in paragraphs:
            if not para_text.strip():
                continue
                
            para = doc.add_paragraph()
            para.alignment = align
            
            if "line" in spacing:
                para.paragraph_format.line_spacing = spacing["line"]
            if "first_line_indent_cm" in spacing:
                para.paragraph_format.first_line_indent = Cm(spacing["first_line_indent_cm"])
            if "space_after_pt" in spacing:
                para.paragraph_format.space_after = Pt(spacing["space_after_pt"])
                
            run = para.add_run(para_text.strip())
            set_font(run, font_family)
            run.font.size = Pt(font_size)