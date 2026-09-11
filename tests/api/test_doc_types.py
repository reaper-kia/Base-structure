import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.api
def test_doc_types_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/doc-types")

    assert response.status_code == 200

    payload = response.json()

    assert [item["id"] for item in payload] == [
        "memo",
        "report",
        "reference",
        "letter",
    ]

    memo = payload[0]

    assert len(memo["requisites"]) == 8
    required_keys = {
        requisite["key"] for requisite in memo["requisites"] if requisite["required"]
    }

    optional_keys = {
        requisite["key"]
        for requisite in memo["requisites"]
        if not requisite["required"]
    }

    assert required_keys == {
        "addressee",
        "author",
        "position",
        "doc_date",
        "reg_number",
        "subject",
        "signature",
    }

    assert optional_keys == {"executor"}

    letter = payload[3]

    reg_number = next(
        requisite
        for requisite in letter["requisites"]
        if requisite["key"] == "reg_number"
    )

    assert reg_number["required"] is True

    reference = payload[2]

    assert len(reference["requisites"]) == 5
    reference_required = {
        requisite["key"]
        for requisite in reference["requisites"]
        if requisite["required"]
    }

    # По официальному перечню организаторов у reference НЕТ отдельного
    # "должность составителя" - формат "Составитель" уже включает должность
    # и ФИО одной строкой (contracts/organizer_rules.md).
    assert reference_required == {"subject", "doc_date", "author", "signature"}
    assert "position" not in {r["key"] for r in reference["requisites"]}
