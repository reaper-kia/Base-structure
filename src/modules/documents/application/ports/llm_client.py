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
    """Граница с ml_service. Бэкенд не знает, что внутри.

    Поля запроса — из contracts/llm_contract.md §2: бэкенд читает
    doc_types/*.yaml и передаёт всё, что нужно ml_service, чтобы тот
    ничего не знал о типах документов сам.
    """

    async def process(
        self,
        *,
        draft: str,
        doc_type: str,
        doc_type_name: str,
        structure_hint: str,
        requisite_keys: list[str],
    ) -> LLMResult: ...
