import pytest

from src.modules.documents.domain.entities import (
    Document,
    Requisite,
)
from src.modules.documents.domain.enums import DocumentChannel, RequisiteStatus
from src.modules.documents.infra.repositories import (
    _to_domain,
    _to_model,
)


@pytest.mark.unit
def test_document_mapping_round_trip() -> None:
    document = Document(
        draft="Исходный текст",
        channel=DocumentChannel.BOT,
        requisites=[
            Requisite(
                key="addressee",
                label="Адресат",
                value=None,
                status=RequisiteStatus.MISSING,
                required=True,
            )
        ],
    )

    restored = _to_domain(_to_model(document))

    assert restored == document
