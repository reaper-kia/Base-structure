from ml_service.main import validate_llm_response


def test_strict_schema_validation():
    keys = ["author", "date"]

    # 1. Валидный ответ
    assert (
        validate_llm_response(
            {"improved_text": "Текст", "author": "Иванов", "date": "10.10.2026"}, keys
        )
        == True
    )

    # 2. Массив вместо строки (критерий 4.3)
    assert (
        validate_llm_response(
            {"improved_text": "Текст", "author": ["Иванов"], "date": "10.10.2026"}, keys
        )
        == False
    )

    # 3. Лишний ключ (критерий 4.3)
    assert (
        validate_llm_response(
            {
                "improved_text": "Текст",
                "author": "Иванов",
                "date": "10",
                "extra": "мусор",
            },
            keys,
        )
        == False
    )

    # 4. Пропущенный ключ (критерий 4.3)
    assert (
        validate_llm_response({"improved_text": "Текст", "author": "Иванов"}, keys)
        == False
    )
