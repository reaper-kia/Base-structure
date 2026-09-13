"""Гарантии HTTP-контракта — contracts/llm_contract.md §2.

Тесты идут по ветке fallback (Ollama в тестах недоступна), и это
осознанно: именно эти гарантии бэкенд обязан получить в самом плохом
сценарии, а не только когда модель отвечает.
"""

from fastapi.testclient import TestClient

from ml_service.main import app

client = TestClient(app)

DRAFT = (
    "Кому: Генеральному директору ООО «Ромашка» Иванову И.И.\n"
    "От кого: начальник отдела аналитики Петров П.П.\n"
    "Дата: 12.03.2025\n"
    "Заголовок: О закупке офисной техники\n\n"
    "кароче надо бы купить три компа, цена 180 000 рублей, "
    "поставка не позднее 25.03.2025"
)

KEYS = ["addressee", "author", "position", "doc_date", "reg_number", "subject"]


def process(draft: str = DRAFT, keys: list[str] | None = None) -> dict:
    response = client.post(
        "/api/v1/process",
        json={
            "draft": draft,
            "doc_type": "memo",
            "doc_type_name": "Служебная записка",
            "structure_hint": "кому -> от кого -> суть -> просьба -> подпись",
            "requisite_keys": keys if keys is not None else KEYS,
            "request_id": "test-request",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_requisites_contain_exactly_requested_keys() -> None:
    """§2: ровно ключи из requisite_keys — ни больше, ни меньше."""
    payload = process()

    assert set(payload["requisites"]) == set(KEYS)


def test_missing_value_is_null_not_empty_string() -> None:
    """§2: отсутствующее значение — это null, а не пустая строка."""
    payload = process()

    assert payload["requisites"]["reg_number"] is None


def test_improved_text_is_never_empty() -> None:
    payload = process()

    assert payload["improved_text"].strip()


def test_fact_guard_is_filled_even_on_fallback() -> None:
    """§2: fact_guard заполнен всегда, даже при is_fallback: true."""
    payload = process()

    assert payload["is_fallback"] is True
    assert payload["fact_guard"]["verdict"] in {"clean", "warning", "blocked"}
    assert payload["fact_guard"]["source_count"] > 0


def test_fallback_reports_reason_and_version() -> None:
    """Деградация должна быть объяснимой: почему и чем обработали."""
    payload = process()

    assert payload["reason_code"] == "model_unavailable"
    assert payload["model_version"] == "rule-based-1.1.0"
    assert payload["latency_ms"] >= 0


def test_fallback_preserves_facts_and_invents_nothing() -> None:
    """Сценарий 4: суммы, даты и условия доходят до результата целыми."""
    payload = process()
    text = payload["improved_text"]

    assert "180 000" in text
    assert "25.03.2025" in text
    assert "не позднее" in text
    assert payload["fact_guard"]["added"] == []


def test_fallback_extracts_only_labelled_requisites() -> None:
    """Помеченные строки разбираются, неназванное остаётся null."""
    payload = process()

    assert payload["requisites"]["addressee"] == (
        "Генеральному директору ООО «Ромашка» Иванову И.И."
    )
    assert payload["requisites"]["doc_date"] == "12.03.2025"
    assert payload["requisites"]["author"] == "Петров П.П."
    assert payload["requisites"]["position"] == "Начальник отдела аналитики"


def test_missing_addressee_is_not_invented() -> None:
    """Сценарий 3: адресата нет — система его не придумывает."""
    payload = process(
        "От кого: начальник отдела аналитики Петров П.П.\n"
        "Прошу выделить средства на закупку трёх компьютеров."
    )

    assert payload["requisites"]["addressee"] is None


def test_request_id_is_echoed() -> None:
    assert process()["request_id"] == "test-request"


def test_empty_draft_is_rejected_with_422() -> None:
    response = client.post(
        "/api/v1/process",
        json={
            "draft": "",
            "doc_type": "memo",
            "doc_type_name": "Служебная записка",
            "structure_hint": "",
            "requisite_keys": ["addressee"],
        },
    )

    assert response.status_code == 422
