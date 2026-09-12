"""Единственная таблица сервиса: documents.

Схема собрана заново под кейс «Документ за 3 шага»: таблицы outbox от
событийной шины бойлерплейта удалены вместе с самой шиной, а started_at,
deadline и reason_code добавлены сразу, а не отдельной миграцией.

Revision ID: 0001_documents
Revises:
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_documents"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        # Черновик пользователя. Не перезаписывается никогда: сценарий 6
        # требует, чтобы после ошибки ИИ исходный текст остался на месте.
        sa.Column("draft", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.String(length=32), nullable=False),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("improved_text", sa.Text(), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("requisites", sa.JSON(), nullable=True),
        sa.Column("fact_guard", sa.JSON(), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Поиск зависших обработок: «всё, что в processing и просрочено».
    op.create_index(
        "ix_documents_status_deadline",
        "documents",
        ["status", "deadline"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_documents_status_deadline", table_name="documents")
    op.drop_table("documents")
