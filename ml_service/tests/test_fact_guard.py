"""Fact Guard — contracts/llm_contract.md §5.

Проверяется не «модель хорошая», а «код ловит подмену фактов».
"""

from ml_service.guard import anchors
from ml_service.guard.fact_guard import check


def verdict(draft: str, result: str) -> str:
    return check(anchors.extract(draft), anchors.extract(result), draft).verdict


def test_clean_when_every_fact_survives() -> None:
    draft = "Прошу отпуск с 10.06.2025 на 14 календарных дней. Петров П.П."
    result = (
        "Прошу предоставить ежегодный оплачиваемый отпуск с 10.06.2025 "
        "сроком на 14 календарных дней. Петров П.П."
    )

    assert verdict(draft, result) == "clean"


def test_warning_when_fact_disappears() -> None:
    """§5.3: потеря — предупреждение, а не блокировка."""
    draft = "Прошу отпуск с 10.06.2025 на 14 календарных дней, а то я устал."
    result = "Прошу предоставить отпуск с 10.06.2025."

    assert verdict(draft, result) == "warning"


def test_blocked_when_model_invents_a_date() -> None:
    """Сценарий 4: появление даты, которой не было, — галлюцинация."""
    draft = "Прошу предоставить отпуск на 14 календарных дней."
    result = "Прошу предоставить отпуск с 01.07.2025 на 14 календарных дней."

    assert verdict(draft, result) == "blocked"


def test_blocked_when_model_invents_a_person() -> None:
    draft = "Прошу согласовать закупку техники."
    result = "Прошу согласовать закупку техники. Иванов И.И."

    assert verdict(draft, result) == "blocked"


def test_date_written_in_words_counts_as_the_same_fact() -> None:
    draft = "Отпуск с 10 июня 2025 года."
    result = "Отпуск с 10.06.2025."

    assert verdict(draft, result) == "clean"


def test_declension_of_surname_is_not_a_new_person() -> None:
    """«Иванову И.И.» в шапке и «Иванов И.И.» в подписи — один человек."""
    draft = "Кому: Иванову И.И. Прошу согласовать."
    result = "Прошу согласовать. Иванов И.И."

    assert verdict(draft, result) == "clean"


def test_organization_without_quotes_matches_quoted_one() -> None:
    draft = "Поставщик ООО ТехноСнаб готов отгрузить товар."
    result = "Поставщик — ООО «ТехноСнаб» — готов осуществить поставку."

    assert verdict(draft, result) == "clean"


def test_split_date_range_is_reformulation_not_hallucination() -> None:
    """«с 10 по 13 марта 2025» -> «с 10 марта 2025 по 13 марта 2025»."""
    draft = "Проверка проведена с 10 по 13 марта 2025 года."
    result = "Проверка проведена в период с 10 марта 2025 года по 13 марта 2025 года."

    assert verdict(draft, result) == "clean"


def test_blocked_when_condition_is_inverted() -> None:
    """Числа сошлись, а смысл перевернулся: «не позднее» -> «не ранее»."""
    draft = "Средства выдать не позднее 18.09.2026."
    result = "Средства выдать не ранее 18.09.2026."

    assert verdict(draft, result) == "blocked"


def test_amount_scale_is_normalized() -> None:
    draft = "Стоимость 50 тыс. руб."
    result = "Стоимость составляет 50 000 руб."

    assert verdict(draft, result) == "clean"


def test_different_units_are_different_facts() -> None:
    draft = "Срок — 5 рабочих дней."
    result = "Срок — 5 календарных дней."

    assert verdict(draft, result) == "blocked"


def test_counters_are_reported() -> None:
    draft = "Сумма 180 000 руб., срок 10.06.2025."
    result = "Сумма 180 000 руб."
    guard = check(anchors.extract(draft), anchors.extract(result), draft)

    assert guard.source_count == 2
    assert guard.preserved_count == 1
    assert guard.lost == ["10.06.2025"]
