from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str


class ProcessResponse(BaseModel):
    improved_text: str
    requisites: dict[str, str | None]
    changes: list[dict] = []
    fact_guard: dict = {}
    is_fallback: bool = False
    model_version: str = "unknown"
    latency_ms: float = 0.0
