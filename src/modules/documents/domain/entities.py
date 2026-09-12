from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional
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
    value: Optional[str]
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
    stage: Optional[ProcessingStage] = ProcessingStage.LLM
    improved_text: Optional[str] = None
    changes: list = field(default_factory=list)
    requisites: list = field(default_factory=list)
    fact_guard: Optional[dict] = None
    is_fallback: bool = False
    error: Optional[dict] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
