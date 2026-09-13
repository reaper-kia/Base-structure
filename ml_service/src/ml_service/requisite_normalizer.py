"""Консервативная нормализация связанных реквизитов.

Модель и rule-based fallback иногда возвращают строку ``От кого`` целиком
в ``author``. Для типов документов с отдельным ``position`` раскладываем
только однозначный формат ``должность + Фамилия И.О.``. Остальные строки
оставляем без изменений: лучше запросить уточнение, чем потерять организацию
или часть имени.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

_PERSON_WITH_INITIALS = re.compile(
    r"^(?P<prefix>.+?)\s+"
    r"(?P<person>[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+"
    r"[А-ЯЁ]\.\s*[А-ЯЁ]\.)$"
)
_ORGANIZATION_FORM = re.compile(
    r"\b(?:ООО|ПАО|ОАО|ЗАО|АО|ИП|ФГБУ|ФГБОУ|ГБУ|МБУ|АНО|НКО|"
    r"ГУП|МУП|ФГУП)\b",
    re.IGNORECASE,
)
_POSITION_HEADS = frozenset(
    {
        "бухгалтер",
        "ведущий",
        "генеральный",
        "главный",
        "директор",
        "заместитель",
        "заведующий",
        "инженер",
        "исполняющий",
        "консультант",
        "менеджер",
        "начальник",
        "председатель",
        "руководитель",
        "секретарь",
        "специалист",
        "сотрудник",
        "эксперт",
        "юрист",
    }
)


def _looks_like_position(value: str) -> bool:
    first_word = value.split(maxsplit=1)[0].strip(".,:;()\u00ab\u00bb").casefold()
    return first_word in _POSITION_HEADS or first_word in {"и.о", "и.о."}


def _capitalize_first(value: str) -> str:
    return value[:1].upper() + value[1:]


def split_author_position(value: str) -> tuple[str, str] | None:
    """Возвращает ``(author, position)`` только для уверенного совпадения."""

    match = _PERSON_WITH_INITIALS.match(value.strip())
    if match is None:
        return None

    prefix = match.group("prefix").strip(" \t,;:\u00a0")
    person = match.group("person")
    organization = _ORGANIZATION_FORM.search(prefix)

    if organization is None:
        if not _looks_like_position(prefix):
            return None
        return person, _capitalize_first(prefix)

    # Формат из официальных черновиков писем:
    # «Генеральный директор ООО «Ромашка» Иванов И.И.».
    position = prefix[: organization.start()].strip(" \t,;:\u00a0")
    organization_name = prefix[organization.start() :].strip()
    if not position or not organization_name or not _looks_like_position(position):
        return None

    return f"{organization_name} {person}", _capitalize_first(position)


def normalize_author_position(
    requisites: Mapping[str, str | None],
) -> dict[str, str | None]:
    """Разделяет author/position, не затирая уже заполненную должность."""

    normalized = dict(requisites)
    if "author" not in normalized or "position" not in normalized:
        return normalized

    author = normalized.get("author")
    if not isinstance(author, str):
        return normalized

    split = split_author_position(author)
    if split is None:
        return normalized

    clean_author, extracted_position = split
    normalized["author"] = clean_author
    if not normalized.get("position"):
        normalized["position"] = extracted_position
    return normalized
