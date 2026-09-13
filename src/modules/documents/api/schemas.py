from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateDocumentRequest(BaseModel):
    draft: str = Field(
        min_length=1,
        max_length=20000,
    )

    doc_type: str = Field(
        min_length=1,
        max_length=32,
    )

    template_id: str = Field(
        min_length=1,
        max_length=64,
    )

    channel: Literal["web", "bot"] = "web"

    @field_validator("draft")
    @classmethod
    def draft_must_contain_text(
        cls,
        value: str,
    ) -> str:
        if not value.strip():
            raise ValueError("Черновик не должен быть пустым")

        # Возвращаем исходную строку без strip().
        return value


class RequisiteSchema(BaseModel):
    key: str
    label: str
    value: str | None
    status: str
    required: bool


class DocumentResponse(BaseModel):
    id: UUID
    status: str
    stage: str | None
    doc_type: str
    template_id: str
    channel: Literal["web", "bot"]
    draft: str
    improved_text: str | None = None
    changes: list[dict] = Field(default_factory=list)
    requisites: list[RequisiteSchema] = Field(default_factory=list)
    fact_guard: dict | None = None
    is_fallback: bool = False
    reason_code: str | None = None
    error: dict | None = None


class UpdateRequisitesRequest(BaseModel):
    values: dict[str, str | None]
    # Ключ попадает сюда только после явного выбора пользователем подсказки,
    # полученной от ReferenceDataSource. По умолчанию PATCH остаётся ручным.
    from_registry: list[str] = Field(default_factory=list)


class UpdateTextRequest(BaseModel):
    """Ручная правка улучшенного текста перед генерацией файла.

    Сценарий 7 задания. Правка пользователя — это его собственные сведения,
    поэтому Fact Guard по ней не проходит: он защищает от выдумок модели,
    а не запрещает человеку дописать в свой документ то, что он знает.
    """

    improved_text: str = Field(min_length=1, max_length=40000)

    @field_validator("improved_text")
    @classmethod
    def text_must_contain_something(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Текст документа не должен быть пустым")
        return value


class ToggleAiFailureRequest(BaseModel):
    enabled: bool


class DocTypeRequisiteResponse(BaseModel):
    key: str
    label: str
    required: bool


class DocTypeResponse(BaseModel):
    id: str
    name: str
    description: str
    requisites: list[DocTypeRequisiteResponse]
