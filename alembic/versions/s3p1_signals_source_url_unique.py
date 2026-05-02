"""signals unique source_url for scout dedup

Revision ID: s3p1_signals_uq
Revises: s3p0_ideas_ext
Create Date: 2026-05-02

"""
from __future__ import annotations

from alembic import op

revision = "s3p1_signals_uq"
down_revision = "s3p0_ideas_ext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM signals a USING signals b
        WHERE a.ctid > b.ctid
          AND a.source_url IS NOT NULL
          AND a.source_url = b.source_url;
        """
    )
    op.create_unique_constraint("uq_signals_source_url", "signals", ["source_url"])


def downgrade() -> None:
    op.drop_constraint("uq_signals_source_url", "signals", type_="unique")
