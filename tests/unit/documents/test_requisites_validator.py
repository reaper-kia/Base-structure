from src.modules.documents.application.services.requisites_validator import validate
from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus


def _by_key(requisites: list[Requisite]) -> dict[str, Requisite]:
    return {requisite.key: requisite for requisite in requisites}


def test_combined_author_is_split_before_backend_validation() -> None:
    requisites = _by_key(
        validate(
            "memo",
            {
                "author": "Начальник отдела аналитики Петров П.П.",
                "position": None,
            },
        )
    )

    assert requisites["author"].value == "Петров П.П."
    assert requisites["author"].status == RequisiteStatus.FOUND_IN_DRAFT
    assert requisites["position"].value == "Начальник отдела аналитики"
    assert requisites["position"].status == RequisiteStatus.FOUND_IN_DRAFT


def test_backend_split_does_not_overwrite_user_position() -> None:
    existing = [
        Requisite(
            key="position",
            label="Должность автора",
            value="Начальник аналитики",
            status=RequisiteStatus.USER_PROVIDED,
            required=True,
        )
    ]

    requisites = _by_key(
        validate(
            "memo",
            {
                "author": "Начальник отдела аналитики Петров П.П.",
                "position": None,
            },
            existing=existing,
        )
    )

    assert requisites["author"].value == "Петров П.П."
    assert requisites["position"].value == "Начальник аналитики"
    assert requisites["position"].status == RequisiteStatus.USER_PROVIDED


def test_reference_author_is_not_split_without_position_field() -> None:
    requisites = _by_key(
        validate(
            "reference",
            {"author": "Руководитель отдела развития Козлов К.К."},
        )
    )

    assert requisites["author"].value == (
        "Руководитель отдела развития Козлов К.К."
    )
