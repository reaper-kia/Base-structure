from uuid import UUID

from pydantic import BaseModel, Field


class CreateDocumentRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str
    template_id: str


class RequisiteSchema(BaseModel):
    key: str
    label: str
    value: str | None
    status: str
    required: bool


class DocumentResponse(BaseModel):
    id: UUID
    status: str
    draft: str
    improved_text: str | None = None
    changes: list[dict] = []
    requisites: list[RequisiteSchema] = []
    fact_guard: dict | None = None
    error: dict | None = None


class UpdateRequisitesRequest(BaseModel):
    values: dict[str, str | None]
