from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    draft: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(32))
    template_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))

    stage: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    improved_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    changes: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    requisites: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    fact_guard: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_fallback: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    error: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
