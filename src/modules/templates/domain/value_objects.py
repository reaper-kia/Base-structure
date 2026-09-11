from __future__ import annotations

from dataclasses import dataclass

from src.modules.templates.domain.exceptions import TemplateRulesInvalidError


@dataclass(frozen=True)
class PageMargins:
    top_mm: float
    bottom_mm: float
    left_mm: float
    right_mm: float

    @classmethod
    def from_dict(cls, raw: dict) -> "PageMargins":
        if not isinstance(raw, dict):
            raise TemplateRulesInvalidError

        for key in ("top_mm", "bottom_mm", "left_mm", "right_mm"):
            value = raw.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TemplateRulesInvalidError
            if value < 0:
                raise TemplateRulesInvalidError

        return cls(
            top_mm=raw["top_mm"],
            bottom_mm=raw["bottom_mm"],
            left_mm=raw["left_mm"],
            right_mm=raw["right_mm"],
        )


@dataclass(frozen=True)
class FontSpec:
    """Гарнитура и кегль основного шрифта."""

    family: str
    size_pt: float

    @classmethod
    def from_dict(cls, raw: dict) -> "FontSpec":
        if not isinstance(raw, dict):
            raise TemplateRulesInvalidError

        family = raw.get("family")
        if not isinstance(family, str) or not family.strip():
            raise TemplateRulesInvalidError

        size = raw.get("size_pt")
        if not isinstance(size, (int, float)) or isinstance(size, bool):
            raise TemplateRulesInvalidError
        if size <= 0:
            raise TemplateRulesInvalidError

        return cls(family=family.strip(), size_pt=size)


@dataclass(frozen=True)
class RequisiteBlock:
    """Один блок в requisites_layout."""

    key: str
    position: str
    style: str | None = None
    bold: bool = False

    @classmethod
    def from_dict(cls, raw: dict) -> "RequisiteBlock":
        if not isinstance(raw, dict):
            raise TemplateRulesInvalidError

        key = raw.get("key")
        if not key or not isinstance(key, str):
            raise TemplateRulesInvalidError

        return cls(
            key=key,
            position=raw.get("position", ""),
            style=raw.get("style"),
            bold=bool(raw.get("bold", False)),
        )


@dataclass(frozen=True)
class TemplateRules:
    """Правила шаблона — неизменяемый объект, валидирует себя сам."""

    page: PageMargins
    font: FontSpec
    layout: tuple[RequisiteBlock, ...]
    raw: dict

    @classmethod
    def from_dict(cls, raw: dict) -> "TemplateRules":
        if not isinstance(raw, dict) or not raw:
            raise TemplateRulesInvalidError

        page = PageMargins.from_dict(raw.get("page") or {})
        font = FontSpec.from_dict(raw.get("font") or {})
        layout = cls._build_layout(raw)

        return cls(page=page, font=font, layout=layout, raw=raw)

    @staticmethod
    def _build_layout(raw: dict) -> tuple[RequisiteBlock, ...]:
        layout_raw = raw.get("requisites_layout")

        if not isinstance(layout_raw, list) or not layout_raw:
            raise TemplateRulesInvalidError

        blocks = [RequisiteBlock.from_dict(block) for block in layout_raw]

        # Маркер «body» — точка вставки улучшенного текста (п. 3.4 задания)
        keys = [block.key for block in blocks]
        if "body" not in keys:
            raise TemplateRulesInvalidError

        return tuple(blocks)
