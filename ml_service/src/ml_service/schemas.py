"""HTTP-контракт ml_service — contracts/llm_contract.md §2.

Модель заполняет только improved_text / requisites / changes.
fact_guard, is_fallback, model_version, latency_ms и reason_code добавляет
сервис после проверки: модель не может свидетельствовать о собственной
честности (§3).
"""

from typing import Literal

from pydantic import BaseModel, Field

# Допустимые типы правок (spelling / punctuation / style / structure)
# живут в llm/schema.py: там они и проверяются при нормализации ответа.
Verdict = Literal["clean", "warning", "blocked"]

# Причина, по которой результат оказался резервным. Пробрасывается в бэкенд
# и дальше во фронт (contracts/api.md §3), чтобы «ИИ не сработал» можно было
# отличить от «модель ответила мусором».
ReasonCode = Literal[
    "model_unavailable",  # Ollama недоступна или ответила не 200
    "schema_invalid",  # ответ не разобрался в схему даже после repair
    "facts_unverified",  # Fact Guard дважды вернул blocked
    "empty_text",  # модель вернула пустой improved_text
]


class ProcessRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str
    doc_type_name: str
    structure_hint: str
    requisite_keys: list[str]
    request_id: str | None = None


class FactGuardResult(BaseModel):
    verdict: Verdict = "clean"
    preserved: list[str] = Field(default_factory=list)
    lost: list[str] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    # Инверсии условий («не позднее» -> «позднее»). Расширение контракта §5.2:
    # факт на месте, но смысл вокруг него перевернулся.
    inverted: list[str] = Field(default_factory=list)
    source_count: int = 0
    preserved_count: int = 0


class ProcessResponse(BaseModel):
    request_id: str | None = None
    improved_text: str
    requisites: dict[str, str | None]
    changes: list[dict] = Field(default_factory=list)
    fact_guard: FactGuardResult
    is_fallback: bool = False
    model_version: str
    latency_ms: float
    reason_code: ReasonCode | None = None


class ModelHealth(BaseModel):
    model_loaded: bool
    model_version: str
    fallback_enabled: bool
    supported_tasks: list[str]
    ollama_url: str
    detail: str | None = None
