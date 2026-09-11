from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    improved_text: str
    requisites: dict[str, str | None]
    changes: list[dict]
    fact_guard: dict
    is_fallback: bool


class LLMClient(Protocol):
    """Граница с ml_service. Бэкенд не знает, что внутри."""

    async def process(self, draft: str, doc_type: str) -> LLMResult: ...
