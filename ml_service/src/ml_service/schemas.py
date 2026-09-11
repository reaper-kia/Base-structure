from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProcessRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str = Field(min_length=1, max_length=32)
    doc_type_name: str = Field(min_length=1)
    structure_hint: str = Field(min_length=1)
    requisite_keys: list[str] = Field(min_length=1)
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class ChangeItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["spelling", "punctuation", "style", "structure"]
    from_: str = Field(alias="from")
    to: str


class FactGuardResult(BaseModel):
    verdict: Literal["clean", "warning", "blocked"] = "clean"
    preserved: list[str] = Field(default_factory=list)
    lost: list[str] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    source_count: int = 0
    preserved_count: int = 0


class ProcessResponse(BaseModel):
    improved_text: str = Field(min_length=1)
    requisites: dict[str, str | None]
    changes: list[ChangeItem] = Field(default_factory=list)
    fact_guard: FactGuardResult
    is_fallback: bool = False
    model_version: str
    latency_ms: float


class ModelHealth(BaseModel):
    model_loaded: bool
    model_version: str
    fallback_enabled: bool
    supported_tasks: list[str]
