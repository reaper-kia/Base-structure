"""Извлечение якорей — contracts/llm_contract.md §5.1.

Пять категорий фактов, которые модель не имеет права ни выдумать, ни
переписать: даты, суммы и величины, ФИО, регистрационные номера, названия
организаций. Плюс шестая, служебная, — условия («не позднее», «только
при»): сам факт может уцелеть, а смысл вокруг него перевернуться.

Регулярки, а не NER: 80% результата за 20% времени. Важно не сделать
категорию слишком жадной — иначе Fact Guard начнёт срабатывать на любой
нормальной переформулировке.
"""

from __future__ import annotations

import re
from typing import Any

MONTHS = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}

CATEGORIES = ("dates", "amounts", "names", "numbers", "orgs", "conditions")

DATE_PATTERN = re.compile(
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа"
    r"|сентября|октября|ноября|декабря)(?:\s+\d{4})?\b",
    re.IGNORECASE,
)

# Единицы могут кончаться точкой ("руб.", "тыс.") или символом "%" — поэтому
# завершающего \b тут быть НЕ должно (после "." или "%" границы слова нет).
# Единица масштаба (тыс./млн.) может стоять перед валютой ("5 млн. руб.").
AMOUNT_PATTERN = re.compile(
    r"\b\d+(?:[.,\s]\d+)*"
    r"(?:\s*(?:тыс|млн|млрд)\.?)?"
    r"\s*(?:руб\.?|рублей|рубля|долл\.?|евро|%|процент(?:ов|а)?"
    r"|рабочих\s+дней|календарных\s+дней|дней|часов|сотрудник(?:ов|а)?"
    r"|кв\.?\s*м\.?|квадратных\s+метров"
    r"|тыс\.?|млн\.?|млрд\.?)",
    re.IGNORECASE,
)

# «Иванов И.И.», «Иванов И. И.» — фамилия плюс инициалы.
INITIALS_PATTERN = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.")

# «Иванов Иван Иванович» — полное ФИО. Отчество обязано выглядеть отчеством,
# иначе в якоря полезут любые три слова с заглавной буквы.
FULL_NAME_PATTERN = re.compile(
    r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+"
    r"([А-ЯЁ][а-яё]+(?:ович|евич|ьевич|овна|евна|ьевна|ична|инична))\b"
)

# «№ 15», «№ 47/2-К», «47-СЗ», «12-ДЗ».
NUMBER_PATTERN = re.compile(
    r"№\s*[0-9]+(?:[/-][0-9A-Za-zА-Яа-яЁё]+)*"
    r"|\b[0-9]{1,5}-[А-ЯЁ]{1,3}\b"
)

# Организация: в кавычках или после организационно-правовой формы.
ORG_QUOTED_PATTERN = re.compile(r"[«\"']([А-ЯЁA-Z][^«»\"']{1,40})[»\"']")
ORG_FORM_PATTERN = re.compile(
    r"\b(?:ООО|ОАО|ЗАО|ПАО|АО|ИП|НКО|ФГУП|МУП)\s+"
    r"[«\"']?([А-ЯЁA-Z][А-Яа-яЁёA-Za-z-]{1,40})[»\"']?"
)

# Условия. Порядок важен: «не позднее» обязано разбираться раньше «позднее».
CONDITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("before", re.compile(r"не\s+позднее(?:\s+чем)?", re.IGNORECASE)),
    ("after", re.compile(r"не\s+ранее(?:\s+чем)?", re.IGNORECASE)),
    ("after", re.compile(r"\bпозднее\b", re.IGNORECASE)),
    ("after", re.compile(r"\bпосле\b", re.IGNORECASE)),
    ("before", re.compile(r"\bдо\s+(?=\d|\«)", re.IGNORECASE)),
    ("before", re.compile(r"\bранее\b", re.IGNORECASE)),
    ("max", re.compile(r"не\s+(?:более|больше|превыш\w+)", re.IGNORECASE)),
    ("min", re.compile(r"не\s+(?:менее|меньше)", re.IGNORECASE)),
    ("only", re.compile(r"\bтолько\b|\bисключительно\b", re.IGNORECASE)),
    ("condition", re.compile(r"при\s+условии", re.IGNORECASE)),
)

_SURNAME_ENDINGS = ("ому", "ого", "ыми", "ым", "ом", "ой", "ей", "у", "а", "е", "ы", "и")
_NON_STRIPPABLE = ("ов", "ев", "ин", "ын")


def _fold(value: str) -> str:
    return value.lower().replace("ё", "е").strip()


def normalize_date(val: str) -> str:
    """«10 июня 2025» и «10.06.2025» должны дать одну и ту же строку."""
    val = _fold(val).replace("-", ".").replace("/", ".")

    for month_name, month_number in MONTHS.items():
        if month_name in val:
            parts = val.split()
            if len(parts) >= 3:
                return f"{parts[0].zfill(2)}.{month_number}.{parts[2]}"
            if len(parts) == 2:
                return f"{parts[0].zfill(2)}.{month_number}"

    parts = val.split(".")
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{parts[2]}"
    return val


def normalize_amount(val: str) -> str:
    """«50 тыс. руб.» и «50 000 руб.» — одна и та же сумма."""
    val = _fold(val)

    # Отсекаем всё, начиная с первой буквы или процента: остаётся число.
    prefix = re.split(r"[а-яa-z%]", val)[0]
    digits = re.sub(r"[^\d]", "", prefix)

    if not digits:
        return val

    number = int(digits)
    if "тыс" in val:
        number *= 1_000
    elif "млн" in val:
        number *= 1_000_000
    elif "млрд" in val:
        number *= 1_000_000_000

    # Единица входит в ключ: 5 рабочих дней и 5 календарных дней — разные факты.
    if "рабоч" in val:
        unit = "work_days"
    elif "календар" in val:
        unit = "cal_days"
    elif "дн" in val:
        unit = "days"
    elif "час" in val:
        unit = "hours"
    elif "руб" in val:
        unit = "rub"
    elif "долл" in val:
        unit = "usd"
    elif "евро" in val:
        unit = "eur"
    elif "%" in val or "процент" in val:
        unit = "percent"
    elif "сотрудник" in val:
        unit = "people"
    elif "кв" in val or "квадратн" in val:
        unit = "sqm"
    else:
        unit = ""

    return f"{number} {unit}".strip()


def normalize_surname(surname: str) -> str:
    """Сводит падежные формы фамилии к одной: «Иванову» и «Иванова» -> «иванов».

    Без этого «Кому: Иванову И.И.» в черновике и «Иванов И.И.» в подписи
    посчитаются разными фактами, и Guard заблокирует нормальный результат.
    """
    stem = _fold(surname)

    if stem.endswith(_NON_STRIPPABLE):
        return stem

    for ending in _SURNAME_ENDINGS:
        if stem.endswith(ending) and len(stem) - len(ending) >= 4:
            return stem[: -len(ending)]
    return stem


def normalize_name(surname: str, first: str, patronymic: str) -> str:
    """«Иванов Иван Иванович» и «Иванову И.И.» -> «иванов и.и.»."""
    return f"{normalize_surname(surname)} {_fold(first)[0]}.{_fold(patronymic)[0]}."


def normalize_org(name: str) -> str:
    return _fold(name).strip("«»\"' ")


def get_context_window(text: str, match: re.Match, window_size: int = 7) -> str:
    """Слова вокруг якоря: по ним проверяются инверсии условий."""
    words = text.split()
    prefix = text[: match.start()].split()
    start = max(0, len(prefix) - window_size)
    match_words = len(match.group().split())
    end = min(len(words), len(prefix) + match_words + window_size)
    return " ".join(words[start:end]).lower()


def _anchor(text: str, match: re.Match, value: str, norm: str) -> dict[str, Any]:
    return {
        "value": value,
        "norm": norm,
        "context": get_context_window(text, match),
    }


def extract(text: str) -> dict[str, list[dict[str, Any]]]:
    """Возвращает якоря по категориям. Пустой текст -> пустые списки."""
    anchors: dict[str, list[dict[str, Any]]] = {key: [] for key in CATEGORIES}

    if not text:
        return anchors

    for match in DATE_PATTERN.finditer(text):
        value = match.group()
        anchors["dates"].append(_anchor(text, match, value, normalize_date(value)))

    for match in AMOUNT_PATTERN.finditer(text):
        value = match.group()
        anchors["amounts"].append(_anchor(text, match, value, normalize_amount(value)))

    seen_names: set[tuple[int, int]] = set()

    for match in FULL_NAME_PATTERN.finditer(text):
        seen_names.add(match.span())
        norm = normalize_name(match.group(1), match.group(2), match.group(3))
        anchors["names"].append(_anchor(text, match, match.group(), norm))

    for match in INITIALS_PATTERN.finditer(text):
        if any(start <= match.start() < end for start, end in seen_names):
            continue
        norm = (
            f"{normalize_surname(match.group(1))} "
            f"{_fold(match.group(2))}.{_fold(match.group(3))}."
        )
        anchors["names"].append(_anchor(text, match, match.group(), norm))

    for match in NUMBER_PATTERN.finditer(text):
        value = match.group()
        norm = re.sub(r"\s+", "", _fold(value)).lstrip("№")
        anchors["numbers"].append(_anchor(text, match, value, norm))

    seen_orgs: set[str] = set()

    for pattern in (ORG_QUOTED_PATTERN, ORG_FORM_PATTERN):
        for match in pattern.finditer(text):
            norm = normalize_org(match.group(1))
            if not norm or norm in seen_orgs:
                continue
            seen_orgs.add(norm)
            anchors["orgs"].append(_anchor(text, match, match.group(1), norm))

    consumed: list[tuple[int, int]] = []

    for kind, pattern in CONDITION_PATTERNS:
        for match in pattern.finditer(text):
            if any(start <= match.start() < end for start, end in consumed):
                continue
            consumed.append(match.span())
            anchors["conditions"].append(
                _anchor(text, match, match.group().strip(), kind)
            )

    return anchors
