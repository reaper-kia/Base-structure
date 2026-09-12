"""Набор черновиков и ожидаемых структурных результатов — §6 контракта.

Проверяется не точный текст (он будет разным при каждом прогоне модели),
а проверяемые утверждения: какие реквизиты обязаны остаться null, какие
якоря обязаны дожить до результата, каких не должно появиться и какой
вердикт обязан вынести Fact Guard.

Тот же набор используется как материал для демонстрации и как защита от
регрессий при правках промпта. В CI модели нет, поэтому прогон идёт по
ветке fallback — это самый строгий случай: если факты выживают без модели,
они выживут и с ней.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ml_service.main import app

DRAFTS_DIR = Path(__file__).parent / "drafts"
CASES = sorted(path.stem.removesuffix(".expected") for path in DRAFTS_DIR.glob("*.expected.json"))

client = TestClient(app)


def load_case(name: str) -> tuple[str, dict]:
    draft = (DRAFTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    expected = json.loads(
        (DRAFTS_DIR / f"{name}.expected.json").read_text(encoding="utf-8")
    )
    return draft, expected


def test_every_draft_has_an_expectation_file() -> None:
    drafts = {path.stem for path in DRAFTS_DIR.glob("*.txt")}

    assert drafts == set(CASES)


@pytest.mark.parametrize("name", CASES)
def test_draft_is_not_empty_and_utf8(name: str) -> None:
    draft, _ = load_case(name)

    assert draft.strip()


@pytest.mark.parametrize("name", CASES)
def test_draft_produces_contract_compliant_response(name: str) -> None:
    draft, expected = load_case(name)

    response = client.post(
        "/api/v1/process",
        json={
            "draft": draft,
            "doc_type": expected["doc_type"],
            "doc_type_name": expected["doc_type_name"],
            "structure_hint": "кому -> от кого -> суть -> просьба -> подпись",
            "requisite_keys": expected["requisite_keys"],
            "request_id": f"draft-{name}",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert set(payload["requisites"]) == set(expected["requisite_keys"])
    assert payload["improved_text"].strip()


@pytest.mark.parametrize("name", CASES)
def test_absent_requisites_are_not_invented(name: str) -> None:
    """Сценарий 3: чего не было в черновике, того не должно появиться."""
    draft, expected = load_case(name)

    response = client.post(
        "/api/v1/process",
        json={
            "draft": draft,
            "doc_type": expected["doc_type"],
            "doc_type_name": expected["doc_type_name"],
            "structure_hint": "",
            "requisite_keys": expected["requisite_keys"],
        },
    )
    requisites = response.json()["requisites"]

    for key in expected["requisites_must_be_null"]:
        assert requisites[key] is None, f"{name}: реквизит {key} выдуман"


@pytest.mark.parametrize("name", CASES)
def test_facts_survive_and_nothing_is_added(name: str) -> None:
    """Сценарий 4: факты доходят до результата, чужие не появляются."""
    draft, expected = load_case(name)

    response = client.post(
        "/api/v1/process",
        json={
            "draft": draft,
            "doc_type": expected["doc_type"],
            "doc_type_name": expected["doc_type_name"],
            "structure_hint": "",
            "requisite_keys": expected["requisite_keys"],
        },
    )
    payload = response.json()
    haystack = " ".join(
        [payload["improved_text"], *[str(value) for value in payload["requisites"].values()]]
    )

    for anchor in expected["anchors_must_survive"]:
        assert anchor in haystack, f"{name}: потерян факт «{anchor}»"

    for anchor in expected["anchors_must_not_appear"]:
        assert anchor not in haystack, f"{name}: появился факт «{anchor}»"

    assert payload["fact_guard"]["verdict"] == expected["fact_guard_verdict"]
    assert payload["fact_guard"]["added"] == []
