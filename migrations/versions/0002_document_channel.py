"""Добавляет канал создания документа: web или bot.

Revision ID: 0002_document_channel
Revises: 0001_documents
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_document_channel"
down_revision: str | None = "0001_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "channel",
            sa.String(length=8),
            nullable=False,
            server_default="web",
        ),
    )
    op.create_check_constraint(
        "ck_documents_channel",
        "documents",
        "channel IN ('web', 'bot')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_documents_channel",
        "documents",
        type_="check",
    )
    op.drop_column("documents", "channel")
