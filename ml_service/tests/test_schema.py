"""Контракт модели и его починка — contracts/llm_contract.md §3.2, §4."""

from ml_service.llm.schema import (
    build_response_schema,
    extract_json,
    normalize_llm_response,
    validate_llm_response,
)

KEYS = ["author", "doc_date"]


def valid_payload() -> dict:
    return {
        "improved_text": "Текст",
        "requisites": {"author": "Иванов И.И.", "doc_date": "10.10.2026"},
        "changes": [],
    }


def test_schema_requires_exactly_requested_keys() -> None:
    schema = build_response_schema(KEYS)
    requisites = schema["properties"]["requisites"]

    assert requisites["required"] == KEYS
    assert requisites["additionalProperties"] is False


def test_valid_response_passes() -> None:
    assert validate_llm_response(valid_payload(), KEYS) is True


def test_array_instead_of_string_is_rejected() -> None:
    payload = valid_payload()
    payload["requisites"]["author"] = ["Иванов"]

    assert validate_llm_response(payload, KEYS) is False


def test_flat_response_without_requisites_object_is_rejected() -> None:
    """Реквизиты обязаны лежать во вложенном объекте, а не в корне."""
    payload = {"improved_text": "Текст", "author": "Иванов И.И."}

    assert validate_llm_response(payload, KEYS) is False


def test_empty_improved_text_is_rejected() -> None:
    payload = valid_payload()
    payload["improved_text"] = "   "

    assert validate_llm_response(payload, KEYS) is False


def test_extra_key_is_dropped_silently() -> None:
    """§3.2: лишний ключ — выбросить молча, а не уходить в fallback."""
    payload = valid_payload()
    payload["requisites"]["мусор"] = "значение"

    assert validate_llm_response(payload, KEYS) is True
    assert set(normalize_llm_response(payload, KEYS)["requisites"]) == set(KEYS)


def test_missing_key_is_added_as_null() -> None:
    payload = {"improved_text": "Текст", "requisites": {"author": "Иванов И.И."}}
    normalized = normalize_llm_response(payload, KEYS)

    assert normalized["requisites"]["doc_date"] is None


def test_empty_string_is_normalized_to_null() -> None:
    payload = valid_payload()
    payload["requisites"]["author"] = "   "
    payload["requisites"]["doc_date"] = "null"

    normalized = normalize_llm_response(payload, KEYS)

    assert normalized["requisites"] == {"author": None, "doc_date": None}


def test_missing_changes_becomes_empty_list() -> None:
    payload = valid_payload()
    payload.pop("changes")

    assert normalize_llm_response(payload, KEYS)["changes"] == []


def test_change_with_unknown_type_is_dropped() -> None:
    payload = valid_payload()
    payload["changes"] = [
        {"type": "style", "from": "а", "to": "б"},
        {"type": "выдумка", "from": "а", "to": "б"},
    ]

    assert len(normalize_llm_response(payload, KEYS)["changes"]) == 1


def test_markdown_fence_is_stripped_without_calling_the_model() -> None:
    """§4, шаг 2: дешёвая починка регуляркой до второго вызова модели."""
    raw = '```json\n{"improved_text": "Текст", "requisites": {}}\n```'

    assert extract_json(raw) == {"improved_text": "Текст", "requisites": {}}


def test_text_around_json_is_stripped() -> None:
    raw = 'Вот результат: {"improved_text": "Текст", "requisites": {}} Готово.'

    assert extract_json(raw) is not None


def test_unrecoverable_answer_returns_none() -> None:
    assert extract_json("совсем не json") is None
    assert extract_json("") is None
