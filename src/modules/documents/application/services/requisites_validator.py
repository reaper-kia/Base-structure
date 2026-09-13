"""Проверка обязательных реквизитов.

Ничего не выдумывает: если значения нет, реквизит уходит со статусом
MISSING и в документе будет помечен явно.
"""

from datetime import date
from pathlib import Path

import yaml

from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus
from src.modules.documents.application.services.requisite_normalizer import (
    normalize_author_position,
)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "doc_types"

# Статусы, которые нельзя затирать повторной обработкой - за ними стоит
# осознанное решение пользователя (TL-05, PATCH /requisites), а не догадка
# системы. Сценарий 6 требует того же для reprocess.
_USER_DECIDED_STATUSES = frozenset(
    {RequisiteStatus.USER_PROVIDED, RequisiteStatus.LEFT_BLANK}
)


def load_doc_type(doc_type: str) -> dict:
    with (_CONFIG_DIR / f"{doc_type}.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate(
    doc_type: str,
    extracted: dict[str, str | None],
    existing: list[Requisite] | None = None,
) -> list[Requisite]:
    """Собирает список реквизитов по схеме типа документа.

    existing - реквизиты документа до этого запуска (PATCH или прошлая
    обработка). Если пользователь уже принял решение по ключу
    (user_provided/left_blank), это решение переносится как есть - LLM не
    имеет права его переписать.
    """

    schema = load_doc_type(doc_type)
    normalized_extracted = normalize_author_position(extracted or {})
    auto = schema.get("auto_fillable", {}) or {}
    existing_by_key = {item.key: item for item in (existing or [])}
    result: list[Requisite] = []

    for item in schema["requisites"]:
        key, label = item["key"], item["label"]
        required = item.get("required", True)

        previous = existing_by_key.get(key)
        if previous is not None and previous.status in _USER_DECIDED_STATUSES:
            result.append(
                Requisite(
                    key=key,
                    label=label,
                    value=previous.value,
                    status=previous.status,
                    required=required,
                )
            )
            continue

        value = normalized_extracted.get(key) or None

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
                required=required,
            )
        )
    return result


def _auto_value(rule: str) -> str | None:
    """Разрешено подставлять только то, что система знает достоверно."""
    if rule == "today":
        return date.today().strftime("%d.%m.%Y")
    return None
