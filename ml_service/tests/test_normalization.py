from ml_service.guard.anchors import normalize_date, normalize_amount

def test_normalization_rules():
    # Даты (эквивалентно и не эквивалентно)
    assert normalize_date("12.09.2026") == normalize_date("12 сентября 2026")
    assert normalize_date("01.01.2026") == normalize_date("1 января 2026")
    assert normalize_date("2025") != normalize_date("2026")
    assert normalize_date("15.03.2025") != normalize_date("15.04.2025")
    
    # Суммы и условия (эквивалентно и не эквивалентно)
    assert normalize_amount("50 тыс. руб.") == normalize_amount("50 000 руб.")
    assert normalize_amount("50 тыс. руб.") != normalize_amount("50 руб.")
    assert normalize_amount("5 рабочих дней") != normalize_amount("5 календарных дней")
    assert normalize_amount("1 млн. руб.") == normalize_amount("1000000 руб.")
