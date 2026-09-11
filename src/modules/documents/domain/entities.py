from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.documents.domain.enums import (
    DocType,
    DocumentStatus,
    ProcessingStage,
    RequisiteStatus,
)


@dataclass
class Requisite:
    key: str
    label: str
    value: str | None
    status: RequisiteStatus
    required: bool


@dataclass
class Document:
    """Черновик пользователя и всё, что с ним сделала система.

    draft не перезаписывается никогда: сценарий 6 требует, чтобы после
    ошибки ИИ исходный текст остался на месте.
    """

    id: UUID = field(default_factory=uuid4)
    draft: str = ""
    doc_type: DocType = DocType.MEMO
    template_id: str = "classic"
    status: DocumentStatus = DocumentStatus.PROCESSING
    stage: ProcessingStage | None = ProcessingStage.LLM
    improved_text: str | None = None
    changes: list[dict] = field(default_factory=list)
    requisites: list[Requisite] = field(default_factory=list)
    fact_guard: dict | None = None
    is_fallback: bool = False
    error: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
