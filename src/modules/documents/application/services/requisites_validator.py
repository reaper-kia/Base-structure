"""Проверка обязательных реквизитов.

Ничего не выдумывает: если значения нет, реквизит уходит со статусом
MISSING и в документе будет помечен явно.
"""

from datetime import date
from pathlib import Path

import yaml

from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "doc_types"


def load_doc_type(doc_type: str) -> dict:
    with (_CONFIG_DIR / f"{doc_type}.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate(doc_type: str, extracted: dict[str, str | None]) -> list[Requisite]:
    schema = load_doc_type(doc_type)
    auto = schema.get("auto_fillable", {}) or {}
    result: list[Requisite] = []

    for item in schema["requisites"]:
        key, label = item["key"], item["label"]
        value = (extracted or {}).get(key) or None

        if value:
            status = RequisiteStatus.FOUND_IN_DRAFT
        elif key in auto:
            value = _auto_value(auto[key])
            status = RequisiteStatus.AUTO_FILLED
        else:
            status = RequisiteStatus.MISSING

        result.append(
            Requisite(
                key=key,
                label=label,
                value=value,
                status=status,
                required=item.get("required", True),
            )
        )
    return result


def _auto_value(rule: str) -> str | None:
    """Разрешено подставлять только то, что система знает достоверно."""
    if rule == "today":
        return date.today().strftime("%d.%m.%Y")
    return None
