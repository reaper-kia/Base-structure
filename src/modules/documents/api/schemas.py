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
    draft: str
    improved_text: str | None = None
    changes: list[dict] = Field(default_factory=list)
    requisites: list[RequisiteSchema] = Field(default_factory=list)
    fact_guard: dict | None = None
    is_fallback: bool = False
    error: dict | None = None


class UpdateRequisitesRequest(BaseModel):
    values: dict[str, str | None]


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
