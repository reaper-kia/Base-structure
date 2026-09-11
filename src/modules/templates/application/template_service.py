from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path

import yaml

from src.modules.templates.domain.exceptions import TemplateMissingError

from src.modules.templates.domain.entities import Template
from src.modules.templates.domain.exceptions import (
    TemplateNotFoundError,
    TemplateRulesInvalidError,
)
from src.modules.templates.domain.value_objects import TemplateRules

logger = logging.getLogger(__name__)

DEFAULT_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
DEFAULT_TEMPLATE_ID = "classic"

class TemplateLoader:

    def __init__(self, assets_dir: Path | str = DEFAULT_ASSETS_DIR) -> None:
        self._assets_dir = Path(assets_dir)

    def list_templates(self) -> list[Template]:
        templates: list[Template] = []

        if not self._assets_dir.exists():
            return templates

        for entry in sorted(self._assets_dir.iterdir()):
            if not entry.is_dir():
                continue

            rules_path = entry / "rules.yaml"
            if not rules_path.exists():
                continue

            templates.append(self._load_entry(entry))

        return templates

    def load(self, template_id: str) -> Template:
        for template in self.list_templates():
            if template.id == template_id and template.available:
                return template

        raise TemplateNotFoundError

    def load_with_fallback(self, template_id: str) -> Template:
        """Загрузка с переходом на запасной шаблон (п. 6.1 задания).

        1. Запрошенный шаблон есть и валиден -> возвращаем как есть.
        2. Нет папки или битый rules.yaml -> берём DEFAULT_TEMPLATE_ID,
           ставим fallback_used=True и человекочитаемую причину.
        3. Повреждён и запасной -> TemplateMissingError (единственный
           случай, когда документ не формируется).
        """
        templates = {t.id: t for t in self.list_templates()}

        requested = templates.get(template_id)
        if requested is not None and requested.available:
            return requested

        fallback = templates.get(DEFAULT_TEMPLATE_ID)
        if fallback is None or not fallback.available:
            raise TemplateMissingError()

        return replace(
            fallback,
            fallback_used=True,
            fallback_reason=(
                f"Шаблон «{template_id}» повреждён, "
                f"применён «{DEFAULT_TEMPLATE_ID}»"
            ),
        )


    def _load_entry(self, entry: Path) -> Template:
        template_id = entry.name
        docx_path = entry / "template.docx"
        rules_path = entry / "rules.yaml"

        try:
            raw_rules = self._read_yaml(rules_path)

            # Валидация целиком живёт в VO.
            # Битые правила → TemplateRulesInvalidError.
            TemplateRules.from_dict(raw_rules)

            return Template(
                id=template_id,
                name=raw_rules.get("name", template_id),
                description=raw_rules.get("description", ""),
                rules=raw_rules,
                docx_path=docx_path if docx_path.exists() else None,
                available=True,
            )
        except yaml.YAMLError:
            return self._unavailable(template_id, docx_path, "битый YAML")
        except TemplateRulesInvalidError:
            return self._unavailable(template_id, docx_path, "невалидные правила")
        except OSError as exc:
            return self._unavailable(template_id, docx_path, f"ошибка чтения: {exc}")

    @staticmethod
    def _read_yaml(rules_path: Path) -> dict:
        return yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    @staticmethod
    def _unavailable(template_id: str, docx_path: Path, reason: str) -> Template:
        logger.warning("Шаблон «%s» недоступен: %s", template_id, reason)
        return Template(
            id=template_id,
            name=template_id,
            description="",
            rules={},
            docx_path=docx_path if docx_path.exists() else None,
            available=False,
        )