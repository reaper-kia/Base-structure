"""Нормализация якорей — contracts/llm_contract.md §5.2.

Без неё «Иванов И.И.» и «Иванов И. И.» посчитаются разными фактами,
и Fact Guard выдаст ложное срабатывание на каждом втором черновике.
"""

from ml_service.guard.anchors import (
    extract,
    normalize_amount,
    normalize_date,
    normalize_org,
    normalize_surname,
)


def test_dates_in_digits_and_words_are_equal() -> None:
    assert normalize_date("12.09.2026") == normalize_date("12 сентября 2026")
    assert normalize_date("01.01.2026") == normalize_date("1 января 2026")


def test_different_dates_stay_different() -> None:
    assert normalize_date("2025") != normalize_date("2026")
    assert normalize_date("15.03.2025") != normalize_date("15.04.2025")


def test_amount_scale_is_expanded() -> None:
    assert normalize_amount("50 тыс. руб.") == normalize_amount("50 000 руб.")
    assert normalize_amount("1 млн. руб.") == normalize_amount("1000000 руб.")


def test_amount_unit_is_part_of_the_fact() -> None:
    assert normalize_amount("50 тыс. руб.") != normalize_amount("50 руб.")
    assert normalize_amount("5 рабочих дней") != normalize_amount("5 календарных дней")


def test_surname_cases_collapse_to_one_form() -> None:
    assert normalize_surname("Иванову") == normalize_surname("Иванов")
    assert normalize_surname("Сидорова") == normalize_surname("Сидорову")
    assert normalize_surname("Фёдорову") == normalize_surname("Федоров")


def test_organization_quotes_are_ignored() -> None:
    assert normalize_org("«Ромашка»") == normalize_org("Ромашка")


def test_full_name_and_initials_are_the_same_person() -> None:
    full = extract("Подпись: Иванов Иван Иванович")["names"][0]["norm"]
    short = extract("Подпись: Иванов И.И.")["names"][0]["norm"]

    assert full == short


def test_registration_numbers_are_extracted() -> None:
    found = {item["norm"] for item in extract("Номер: 47-СЗ, вх. № 12/3")["numbers"]}

    assert "47-сз" in found
    assert "12/3" in found


def test_conditions_are_classified_by_direction() -> None:
    kinds = {item["norm"] for item in extract("выдать не позднее 18.09.2026")["conditions"]}

    assert kinds == {"before"}


def test_empty_text_gives_empty_anchors() -> None:
    assert all(not values for values in extract("").values())
