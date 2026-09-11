"""Извлечение и нормализация фактов, которые модель не должна менять."""

import re


PATTERNS: dict[str, str] = {
    "date": (
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|"
        r"августа|сентября|октября|ноября|декабря)(?:\s+\d{2,4})?\b"
    ),
    "amount": (
        r"\b\d[\d \u00a0]*(?:[.,]\d+)?\s*(?:(?:тыс|млн)\.?\s*)?"
        r"(?:руб(?:\.|лей|ля)?|₽)(?=\s|[.,;:!?)]|$)"
        r"|\b\d[\d \u00a0]*(?:[.,]\d+)?\s*%"
        r"|\b\d[\d \u00a0]*(?:[.,]\d+)?\s*"
        r"(?:(?:календарных|рабочих)\s+)?"
        r"(?:дней|дня|день|часов|часа|час)\b"
        r"|\b\d[\d \u00a0]*(?:[.,]\d+)?\s*"
        r"(?:шт\.?|штук(?:а|и)?)\b"
    ),
    "fio": (
        r"\b[А-ЯЁ][а-яё-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\."
        r"|\b[А-ЯЁ][а-яё-]+\s+[А-ЯЁ][а-яё-]+\s+"
        r"[А-ЯЁ][а-яё-]*(?:ович|евич|ич|овна|евна|ична)\b"
    ),
    "number": r"(?:№|N)\s*[A-Za-zА-Яа-яЁё0-9/_-]+",
    "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": (
        r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[)\s-]*\d{3}" r"[\s-]*\d{2}[\s-]*\d{2}(?!\d)"
    ),
    "org": r"«[^»]{2,60}»",
}


def normalize(anchor: str) -> str:
    """Нормализует представление факта, не меняя его смысл."""

    if re.fullmatch(
        PATTERNS["phone"],
        anchor.strip(),
        flags=re.IGNORECASE,
    ):
        digits = re.sub(r"\D", "", anchor)

        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]

        return f"phone:{digits}"

    normalized = anchor.replace("\u00a0", " ").lower().replace("ё", "е")

    normalized = re.sub(
        r"(?<=\d)[/-](?=\d)",
        ".",
        normalized,
    )
    normalized = re.sub(
        r"(?<=[a-zа-я])\.",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"(?<=\d)\s+(?=\d)",
        "",
        normalized,
    )
    normalized = re.sub(r"\s*%", "%", normalized)
    normalized = re.sub(
        r"\bруб(?:лей|ля)?\b",
        "руб",
        normalized,
    )
    normalized = re.sub(
        r"([№n])\s+",
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )

    return " ".join(normalized.split()).strip(" ,;:")


def extract(text: str) -> dict[str, list[str]]:
    """Извлекает факты без учёта регистра исходного текста."""

    result: dict[str, list[str]] = {}

    for kind, pattern in PATTERNS.items():
        values = [
            match.group(0).strip()
            for match in re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        ]

        if values:
            result[kind] = values

    return result
