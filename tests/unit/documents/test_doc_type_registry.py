import pytest

from src.modules.documents.application.services.doc_type_registry import (
    get_doc_type,
    list_doc_types,
)
from src.modules.documents.domain.exceptions import DocTypeNotFound


@pytest.mark.unit
def test_doc_types_have_fixed_order() -> None:
    assert [spec.id for spec in list_doc_types()] == [
        "memo",
        "report",
        "reference",
        "letter",
    ]


@pytest.mark.unit
def test_unknown_doc_type_raises_domain_error() -> None:
    with pytest.raises(DocTypeNotFound):
        get_doc_type("unknown")
