from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path
import zipfile

import yaml
from docx import Document

from src.core.config import settings
from src.modules.templates.domain.entities import Template
from src.modules.templates.domain.exceptions import (
    TemplateMissingError,
    TemplateNotFoundError,
    TemplateRulesInvalidError,
)
from src.modules.templates.domain.value_objects import TemplateRules

logger = logging.getLogger(__name__)

DEFAULT_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def user_templates_dir() -> Path:
    """Каталог пользовательских шаблонов (монтируется томом, доступен на запись)."""
    return Path(settings.user_templates_dir)
DOC_TYPES_DIR = (
    Path(__file__).resolve().parents[2] / "documents" / "config" / "doc_types"
)
DEFAULT_TEMPLATE_ID = "classic"
REQUIRED_DOCX_PARTS = ("[Content_Types].xml", "word/document.xml")


def required_requisite_keys() -> set[str]:
    keys: set[str] = set()
    if not DOC_TYPES_DIR.exists():
        return keys
    for path in sorted(DOC_TYPES_DIR.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for req in spec.get("requisites", []):
            if isinstance(req, dict) and "key" in req:
                is_required = req.get("required")
                if is_required is None or is_required:
                    keys.add(req["key"])
    return keys


def layout_keys(rules: dict) -> set[str]:
    """Все ключи реквизитов, у которых в раскладке есть место.

    Реквизит может стоять и сам по себе, и внутри составного блока:
    строки таблицы (`rows[].value_key`), строки «Дата: … Номер: …»
    (`parts[].key`) и блока подписи (`keys[]`). Если не собирать их все,
    проверка покрытия из B2-01 решит, что места нет, и объявит рабочий
    шаблон недоступным.
    """
    keys: set[str] = set()

    for block in rules.get("requisites_layout", []):
        if "key" in block:
            keys.add(block["key"])
        for row in block.get("rows", []):
            if "value_key" in row:
                keys.add(row["value_key"])
        for part in block.get("parts", []):
            if "key" in part:
                keys.add(part["key"])
        keys.update(block.get("keys", []))

    keys.discard("body")
    return keys


def build_description(rules: dict) -> str:
    """Честное описание шаблона: только факты, прочитанные из правил."""
    font = rules["font"]
    page = rules["page"]
    spacing = rules.get("spacing", {})

    parts = [
        f"{font['family']} {font['size_pt']} pt",
        f"поля {page['left_mm']}/{page['right_mm']}/{page['top_mm']}/{page['bottom_mm']} мм "
        f"(лево/право/верх/низ)",
    ]
    if "line" in spacing:
        parts.append(f"междустрочный интервал {spacing['line']}")
    if spacing.get("first_line_indent_cm"):
        parts.append(f"красная строка {spacing['first_line_indent_cm']} см")
    if any(
        b.get("type") == "table" or b.get("layout") == "table"
        for b in rules.get("requisites_layout", [])
    ):
        parts.append("таблица-шапка «Кому / От кого»")
    footer_text = rules.get("header_footer", {}).get("footer", {}).get("text", "")
    if "{page}" in footer_text:
        parts.append("нумерация страниц в футере")
    elif footer_text:
        parts.append("в футере — тема и дата документа")
    parts.append(
        {
            "justify": "текст по ширине",
            "both": "текст по ширине",
            "left": "текст по левому краю",
        }.get(rules.get("alignment", "left"), f"выравнивание: {rules.get('alignment')}")
    )
    return "; ".join(parts) + "."


def _docx_is_usable(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                return False
            names = set(z.namelist())
            if not all(part in names for part in REQUIRED_DOCX_PARTS):
                return False
        Document(path)  # финальная проба: python-docx реально открывает файл
        return True
    except Exception as exc:  # noqa: BLE001 - проба пригодности: список исключений
        logger.debug("DOCX %s не прошёл пробу пригодности: %s", path, exc)
        return False


def all_spec_keys() -> set[str]:
    keys: set[str] = set()
    if not DOC_TYPES_DIR.exists():
        return keys
    for path in sorted(DOC_TYPES_DIR.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for req in spec.get("requisites", []):
            if isinstance(req, dict) and "key" in req:
                keys.add(req["key"])
    return keys


class TemplateLoader:
    """Читает шаблоны из двух каталогов: встроенных и загруженных.

    Встроенные лежат в образе и доступны только на чтение — прод-контейнер
    поднят с `read_only: true`. Шаблоны, которые загрузил пользователь,
    живут в отдельном каталоге на томе. Имя встроенного шаблона переопределить
    нельзя: иначе загрузкой файла можно было бы подменить classic.
    """

    def __init__(
        self,
        assets_dir: Path | str = DEFAULT_ASSETS_DIR,
        user_dir: Path | str | None = None,
    ) -> None:
        self._assets_dir = Path(assets_dir)
        self._explicit_user_dir = Path(user_dir) if user_dir is not None else None

    @property
    def user_dir(self) -> Path:
        """Читается на каждый вызов: загрузчик создаётся один раз при импорте,
        а каталог может быть переопределён настройкой позже (и в тестах)."""
        if self._explicit_user_dir is not None:
            return self._explicit_user_dir
        return user_templates_dir()

    def list_templates(self) -> list[Template]:
        templates: list[Template] = []
        seen: set[str] = set()

        for directory in (self._assets_dir, self.user_dir):
            if not directory.is_dir():
                continue

            for entry in sorted(directory.iterdir()):
                if not entry.is_dir() or entry.name in seen:
                    continue
                if not (entry / "rules.yaml").exists():
                    continue

                seen.add(entry.name)
                templates.append(self._load_entry(entry))

        return templates

    def load(self, template_id: str) -> Template:
        for template in self.list_templates():
            if template.id == template_id and template.available:
                return template

        raise TemplateNotFoundError

    def load_with_fallback(self, template_id: str) -> Template:
        """Загрузка с переходом на запасной шаблон (п. 6.1 задания)."""
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
                f"Шаблон «{template_id}» повреждён, применён «{DEFAULT_TEMPLATE_ID}»"
            ),
        )

    def _load_entry(self, entry: Path) -> Template:
        template_id = entry.name
        docx_path = entry / "template.docx"
        rules_path = entry / "rules.yaml"

        try:
            raw_rules = self._read_yaml(rules_path)

            # Валидация структуры правил целиком живёт в VO.
            # Битые правила → TemplateRulesInvalidError.
            TemplateRules.from_dict(raw_rules)

            # Проверка покрытия: у каждого обязательного реквизита
            # должно быть место в раскладке (B2-01).
            missing = required_requisite_keys() - layout_keys(raw_rules)
            if missing:
                logger.error(
                    "Шаблон «%s»: раскладка не покрывает обязательные реквизиты %s",
                    template_id,
                    sorted(missing),
                )
                raise TemplateRulesInvalidError

            # Предупреждение о необязательных ключах без места в раскладке:
            # они не роняют загрузку, но молча не доедут до документа (B2-04).
            lost_optional = (all_spec_keys() - required_requisite_keys()) - layout_keys(
                raw_rules
            )
            if lost_optional:
                logger.warning(
                    "Шаблон «%s»: необязательные ключи без места в раскладке %s — "
                    "они не попадут в документ",
                    template_id,
                    sorted(lost_optional),
                )

            # Пригодность базового DOCX проверяем ЗДЕСЬ, а не в момент генерации (B2-05).
            # base_docx: none в rules.yaml — легальный режим «шаблон только из правил».
            base_docx_mode = raw_rules.get("base_docx", "required")
            docx_exists = docx_path.exists()

            if base_docx_mode == "none":
                docx_to_use = (
                    docx_path if (docx_exists and _docx_is_usable(docx_path)) else None
                )
            elif not docx_exists:
                return self._unavailable(
                    template_id,
                    "нет template.docx, а rules не объявляют режим только правил (base_docx: none)",
                )
            elif not _docx_is_usable(docx_path):
                return self._unavailable(
                    template_id,
                    "template.docx повреждён: пакет не открывается или нет обязательных частей",
                )
            else:
                docx_to_use = docx_path

            return Template(
                id=template_id,
                name=raw_rules.get("name", template_id),
                description=build_description(raw_rules),
                rules=raw_rules,
                docx_path=docx_to_use,
                available=True,
            )
        except yaml.YAMLError:
            return self._unavailable(template_id, "битый YAML")
        except TemplateRulesInvalidError:
            return self._unavailable(
                template_id, "невалидные правила или дыра в покрытии"
            )
        except OSError as exc:
            return self._unavailable(template_id, f"ошибка чтения: {exc}")

    @staticmethod
    def _read_yaml(rules_path: Path) -> dict:
        return yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    @staticmethod
    def _unavailable(template_id: str, reason: str) -> Template:
        logger.warning("Шаблон «%s» недоступен: %s", template_id, reason)
        return Template(
            id=template_id,
            name=template_id,
            description="",
            rules={},
            docx_path=None,
            available=False,
        )
