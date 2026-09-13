from datetime import date

from pydantic import BaseModel, Field


class SourceHealthResponse(BaseModel):
    status: str
    message: str


class SuggestionResponse(BaseModel):
    key: str
    value: str
    source: str
    document: str
    date: date


class SuggestionsResponse(BaseModel):
    health: SourceHealthResponse
    suggestions: list[SuggestionResponse] = Field(default_factory=list)
    requires_user_confirmation: bool = True
