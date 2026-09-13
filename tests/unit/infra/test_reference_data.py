from datetime import date

import pytest

from src.modules.reference_data.domain.models import Suggestion
from src.modules.reference_data.infra.null_source import NullReferenceSource


@pytest.mark.unit
def test_null_reference_source_without_config_is_safe() -> None:
    source = NullReferenceSource()

    assert source.suggest("addressee", "Иван") == []
    assert source.health().status.value == "not_configured"
    assert source.health().message == "Источник справочных данных не настроен"


@pytest.mark.unit
def test_suggestion_requires_complete_provenance() -> None:
    with pytest.raises(ValueError, match="происхождение"):
        Suggestion(
            key="addressee",
            value="Иванов И.И.",
            source="Корпоративный справочник",
            document="",
            source_date=date(2026, 9, 13),
        )
