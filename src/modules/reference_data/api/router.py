from fastapi import APIRouter, Depends, Query

from src.modules.reference_data.api.dependencies import get_reference_source
from src.modules.reference_data.api.schemas import (
    SourceHealthResponse,
    SuggestionResponse,
    SuggestionsResponse,
)
from src.modules.reference_data.application.ports import ReferenceDataSource

router = APIRouter(prefix="/api/reference-data", tags=["reference-data"])


@router.get("/suggestions", response_model=SuggestionsResponse)
def suggest_requisite_values(
    key: str = Query(min_length=1, max_length=128),
    query: str = Query(default="", max_length=512),
    source: ReferenceDataSource = Depends(get_reference_source),
) -> SuggestionsResponse:
    """Возвращает только подсказки; применение остаётся за пользователем."""
    health = source.health()
    suggestions = source.suggest(key, query)
    return SuggestionsResponse(
        health=SourceHealthResponse(
            status=health.status.value,
            message=health.message,
        ),
        suggestions=[
            SuggestionResponse(
                key=item.key,
                value=item.value,
                source=item.source,
                document=item.document,
                date=item.source_date,
            )
            for item in suggestions
        ],
    )
