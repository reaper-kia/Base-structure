"""add deadline

Revision ID: 8a9b0c1d2e3f
Revises: 287f0b27b4f2
Create Date: 2026-09-11 12:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "8a9b0c1d2e3f"
down_revision = "287f0b27b4f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("documents", "deadline")
