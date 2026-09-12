from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMResult:
    improved_text: str
    requisites: dict
    changes: list = field(default_factory=list)
    fact_guard: dict = field(default_factory=dict)
    is_fallback: bool = False
    model_version: str = "unknown"


class LLMClient(Protocol):
    async def process(
        self,
        *,
        draft: str,
        doc_type: str,
        doc_type_name: str,
        structure_hint: str,
        requisite_keys: list[str],
    ) -> LLMResult:
        ...