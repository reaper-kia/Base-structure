"""Fact Guard — contracts/llm_contract.md §5.

Детерминированная защита от галлюцинаций: не промпт, а код. Все команды
напишут в промпте «не выдумывай» — мы это проверяем.

Правила вердикта (§5.2):

| Результат сверки            | verdict   | что дальше                  |
|-----------------------------|-----------|-----------------------------|
| added пуст, lost пуст       | clean     | принять                     |
| added пуст, lost непуст     | warning   | принять, фронт предупредит  |
| added непуст                | blocked   | перегенерация, затем fallback |

Почему lost — предупреждение, а не блокировка: модель может законно убрать
якорь вместе с эмоциональной вставкой, внутри которой было число (§5.3).
Появление же факта, которого не было в черновике, — ровно та галлюцинация,
которую проверяет сценарий 4.

Два расширения контракта, оба сужают блокировку, а не расширяют:

1. **Проверка на переформулировку.** «с 10 по 13 марта 2025 года» и
   «с 10 марта 2025 года по 13 марта 2025 года» — один и тот же факт, но во
   втором случае появляется «новая» дата. Прежде чем блокировать, сверяем
   цифры и корни слов с исходным текстом: если всё это в черновике было,
   модель переформулировала, а не выдумала.
2. **Инверсия условий.** Факт может уцелеть, а смысл вокруг него —
   перевернуться: «не позднее 18.09» -> «не ранее 18.09». Числа сходятся,
   но документ говорит обратное. Это блокировка.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# Категории, по которым считается вердикт (§5.1). conditions обрабатываются
# отдельно: это не факты, а модальность вокруг них.
FACT_CATEGORIES = ("dates", "amounts", "names", "numbers", "orgs")

# Пары взаимно противоположных условий. Потеря одного вместе с появлением
# другого = смысл перевернулся.
OPPOSITE_CONDITIONS = {
    ("before", "after"),
    ("after", "before"),
    ("max", "min"),
    ("min", "max"),
}


@dataclass
class GuardResult:
    verdict: str = "clean"
    preserved: list[str] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    inverted: list[str] = field(default_factory=list)
    source_count: int = 0
    preserved_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "preserved": self.preserved,
            "lost": self.lost,
            "added": self.added,
            "inverted": self.inverted,
            "source_count": self.source_count,
            "preserved_count": self.preserved_count,
        }


def _fold(value: str) -> str:
    return value.lower().replace("ё", "е")


def _digits(value: str) -> list[str]:
    return re.findall(r"\d+", value)


def _word_stems(value: str) -> list[str]:
    """Корни слов длиной от 4 букв: хватает, чтобы поймать падежную форму."""
    return [word[:4] for word in re.findall(r"[а-яa-z]{4,}", _fold(value))]


def is_reformulation(value: str, source_text: str) -> bool:
    """Похоже ли, что «новый» якорь собран из того, что уже было в черновике.

    Все числа и все корни слов якоря должны встречаться в исходном тексте.
    Если хоть одного нет — это новый факт, а не перестановка старого.
    """
    if not source_text:
        return False

    folded_source = _fold(source_text)
    source_digits = Counter(_digits(folded_source))

    for digit_group in _digits(value):
        if source_digits[digit_group] == 0:
            return False

    return all(stem in folded_source for stem in _word_stems(value))


def _condition_kinds(anchors: dict[str, list[dict[str, Any]]]) -> Counter:
    return Counter(item["norm"] for item in anchors.get("conditions", []))


def _find_inversions(
    source_anchors: dict[str, list[dict[str, Any]]],
    result_anchors: dict[str, list[dict[str, Any]]],
) -> list[str]:
    source_kinds = _condition_kinds(source_anchors)
    result_kinds = _condition_kinds(result_anchors)

    lost_kinds = {kind for kind, n in source_kinds.items() if result_kinds[kind] < n}
    gained_kinds = {kind for kind, n in result_kinds.items() if source_kinds[kind] < n}

    inversions: list[str] = []
    for lost_kind in sorted(lost_kinds):
        for gained_kind in sorted(gained_kinds):
            if (lost_kind, gained_kind) in OPPOSITE_CONDITIONS:
                source_value = next(
                    item["value"]
                    for item in source_anchors["conditions"]
                    if item["norm"] == lost_kind
                )
                result_value = next(
                    item["value"]
                    for item in result_anchors["conditions"]
                    if item["norm"] == gained_kind
                )
                inversions.append(f"{source_value} -> {result_value}")

    return inversions


def check(
    source_anchors: dict[str, list[dict[str, Any]]],
    result_anchors: dict[str, list[dict[str, Any]]],
    source_text: str = "",
) -> GuardResult:
    """Сверяет якоря черновика и результата. Ничего не знает про модель."""
    preserved: list[str] = []
    lost: list[str] = []
    added: list[str] = []

    for category in FACT_CATEGORIES:
        source_items = source_anchors.get(category, [])
        result_items = list(result_anchors.get(category, []))

        # Списки, а не множества: важна кратность («две суммы по 50 000»).
        available = [item["norm"] for item in result_items]

        for item in source_items:
            if item["norm"] in available:
                preserved.append(item["value"])
                available.remove(item["norm"])
            else:
                lost.append(item["value"])

        for leftover_norm in available:
            value = next(
                item["value"] for item in result_items if item["norm"] == leftover_norm
            )
            # Переформулировка уже имевшегося факта — не галлюцинация.
            if is_reformulation(value, source_text):
                preserved.append(value)
                continue
            added.append(value)

    inverted = _find_inversions(source_anchors, result_anchors)

    if added or inverted:
        verdict = "blocked"
    elif lost:
        verdict = "warning"
    else:
        verdict = "clean"

    return GuardResult(
        verdict=verdict,
        preserved=preserved,
        lost=lost,
        added=added,
        inverted=inverted,
        source_count=sum(
            len(source_anchors.get(category, [])) for category in FACT_CATEGORIES
        ),
        preserved_count=len(preserved),
    )
