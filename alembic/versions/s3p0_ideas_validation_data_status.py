"""ideas validation_data_json and status

Revision ID: s3p0_ideas_ext
Revises:
Create Date: 2026-05-02

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s3p0_ideas_ext"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ideas",
        sa.Column("validation_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "ideas",
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
    )


def downgrade() -> None:
    op.drop_column("ideas", "status")
    op.drop_column("ideas", "validation_data_json")
