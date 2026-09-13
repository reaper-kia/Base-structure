from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TWIPS_PER_MM = 56.6929  # п. 7.2: pgMar хранит твипы, 1 мм = 56.7 твипа

JC_MAP = {"both": "justify", "left": "left", "center": "center", "right": "right"}

# Расположение реквизитов из DOCX автоматически не вычитывается: в файле
# лежат абзацы, а не смысл. Берём раскладку «Классического корпоративного» —
# она покрывает обязательные реквизиты всех четырёх типов, поэтому
# загруженный шаблон сразу проходит проверку покрытия и доступен в работе.
# Пользователь может поправить rules.yaml руками.
DEFAULT_LAYOUT: list[dict[str, Any]] = [
    {"key": "addressee", "position": "top_right"},
    {"key": "author", "position": "top_right"},
    {
        "key": "date_number",
        "type": "line",
        "position": "top_left",
        "parts": [
            {"label": "Дата:", "key": "doc_date"},
            {"label": "Номер:", "key": "reg_number"},
        ],
    },
    {"key": "doc_title", "type": "doc_title", "position": "center", "bold": True},
    {"key": "subject", "position": "center", "bold": True},
    {"key": "salutation", "position": "left"},
    {"key": "body", "position": "body"},
    {
        "key": "signature_block",
        "type": "signature",
        "position": "bottom_left",
        "keys": ["position", "signature"],
    },
    {"key": "executor", "position": "bottom_left", "font_size_pt": 10},
]

# Плейсхолдеры колонтитулов образца («[Название организации] | [Дата]»)
# превращаются в токены правил. Иначе на каждой странице загруженного
# шаблона печаталась бы квадратная скобка вместо значения.
PLACEHOLDER_PATTERN = re.compile(r"\[([^\]]+)\]")
PLACEHOLDER_TOKENS = {
    "название организации": "{org_name}",
    "организация": "{org_name}",
    "название документа": "{doc_type_name}",
    "тип документа": "{doc_type_name}",
    "дата": "{doc_date}",
    "номер": "{reg_number}",
    "тема": "{subject}",
    "заголовок": "{subject}",
    "номер страницы": "{page}",
    "страница": "{page}",
}


def _placeholders_to_tokens(text: str) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1).strip().lower()
        return PLACEHOLDER_TOKENS.get(name, match.group(0))

    return PLACEHOLDER_PATTERN.sub(replace, text)


class NotADocxError(ValueError):
    """Файл не является DOCX (для HTTP 422)."""


def _w(tag: str) -> str:
    return f"{{{W}}}{tag}"


def parse_docx_template(data: bytes) -> tuple[dict[str, Any], list[str]]:
    """Извлекает правила оформления из DOCX. Возвращает (rules, warnings)."""
    warnings: list[str] = []
    bio = io.BytesIO(data)

    if not zipfile.is_zipfile(bio):
        raise NotADocxError("Файл не является DOCX")

    with zipfile.ZipFile(bio) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise NotADocxError("В архиве нет word/document.xml")

        rules: dict[str, Any] = {
            "name": "",
            "description": "Распознан автоматически из загруженного DOCX",
            "page": {"top_mm": 20, "bottom_mm": 20, "left_mm": 30, "right_mm": 15},
            "font": {"family": "Times New Roman", "size_pt": 14},
            "spacing": {"line": 1.5, "first_line_indent_cm": 1.25, "space_after_pt": 0},
            "alignment": "justify",
            "header_footer": {"header": {"text": ""}, "footer": {"text": ""}},
            "requisites_layout": [dict(b) for b in DEFAULT_LAYOUT],
        }

        # --- Поля страницы: document.xml → sectPr → pgMar ---
        doc_root = ET.fromstring(z.read("word/document.xml"))
        pg_mar = doc_root.find(f".//{_w('sectPr')}/{_w('pgMar')}")
        if pg_mar is not None:
            for rule_key, attr in (
                ("top_mm", "top"),
                ("bottom_mm", "bottom"),
                ("left_mm", "left"),
                ("right_mm", "right"),
            ):
                raw = pg_mar.get(_w(attr))
                if raw is not None:
                    rules["page"][rule_key] = round(int(raw) / TWIPS_PER_MM, 1)
        else:
            warnings.append("Не найден sectPr/pgMar — применены поля по умолчанию")

        # --- Гарнитура, кегль, интервал: styles.xml → стиль Normal ---
        if "word/styles.xml" in names:
            styles_root = ET.fromstring(z.read("word/styles.xml"))
            normal = None
            for style in styles_root.findall(_w("style")):
                if (
                    style.get(_w("styleId")) == "Normal"
                    or style.get(_w("default")) == "1"
                ):
                    normal = style
                    break
            if normal is None:
                warnings.append(
                    "Нет явного стиля Normal — применены значения по умолчанию"
                )
            else:
                rpr = normal.find(_w("rPr"))
                if rpr is not None:
                    rfonts = rpr.find(_w("rFonts"))
                    ascii_font = rfonts.get(_w("ascii")) if rfonts is not None else None
                    if ascii_font:
                        rules["font"]["family"] = ascii_font
                    sz = rpr.find(_w("sz"))
                    size_value = sz.get(_w("val")) if sz is not None else None
                    if size_value:
                        rules["font"]["size_pt"] = int(size_value) / 2
                ppr = normal.find(_w("pPr"))
                if ppr is not None:
                    spacing = ppr.find(_w("spacing"))
                    if spacing is not None:
                        line_value = spacing.get(_w("line"))
                        if line_value:
                            rules["spacing"]["line"] = round(int(line_value) / 240, 2)
                        after_value = spacing.get(_w("after"))
                        if after_value:
                            rules["spacing"]["space_after_pt"] = int(after_value) / 20
                    ind = ppr.find(_w("ind"))
                    first_line = ind.get(_w("firstLine")) if ind is not None else None
                    if first_line:
                        rules["spacing"]["first_line_indent_cm"] = round(
                            int(first_line) / TWIPS_PER_MM / 10, 2
                        )
                    jc = ppr.find(_w("jc"))
                    if jc is not None:
                        alignment = jc.get(_w("val"))
                        rules["alignment"] = JC_MAP.get(alignment or "", "justify")
        else:
            warnings.append("Отсутствует styles.xml — применены значения по умолчанию")

        # --- Колонтитулы: header1.xml / footer1.xml ---
        for kind in ("header", "footer"):
            pattern = re.compile(rf"word/{kind}\d*\.xml")
            for n in names:
                if pattern.fullmatch(n):
                    part_root = ET.fromstring(z.read(n))
                    text = " ".join(
                        t.text or "" for t in part_root.iter(_w("t"))
                    ).strip()
                    # Фигурные скобки из чужого файла сломали бы подстановку
                    # токенов колонтитула — убираем их до маппинга.
                    text = text.replace("{", "").replace("}", "")
                    text = _placeholders_to_tokens(text)

                    # Поле PAGE хранит номер отдельно от текста: в w:t лежит
                    # закэшированное «1». Без этой ветки у загруженного
                    # шаблона на каждой странице печаталась бы единица.
                    has_page_field = any(
                        "PAGE" in (node.text or "")
                        for node in part_root.iter(_w("instrText"))
                    )
                    if has_page_field:
                        text = re.sub(r"\b\d+\b", "", text).strip()
                        text = f"{text} {{page}}".strip()

                    rules["header_footer"][kind]["text"] = text
                    break

        # Расположение реквизитов автоматически определить нельзя (п. 7.2) —
        # остаётся дефолтным, пользователь правит вручную.
        if not rules["name"]:
            rules["name"] = "Загруженный шаблон"

        return rules, warnings
