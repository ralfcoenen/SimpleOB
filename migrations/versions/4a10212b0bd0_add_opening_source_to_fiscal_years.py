"""add opening source to fiscal years

Revision ID: 4a10212b0bd0
Revises: 7392d6cc6892
Create Date: 2026-08-09 14:16:26.633481
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4a10212b0bd0"
down_revision: str | Sequence[str] | None = "7392d6cc6892"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    """Ergänzt die Herkunft eines eröffneten Geschäftsjahres."""

    op.execute(
        """
        ALTER TABLE wirtschaftsjahre
        ADD COLUMN opening_source_id INTEGER
        REFERENCES wirtschaftsjahre(id)
        """
    )

def downgrade() -> None:
    """Entfernt die Herkunft eines eröffneten Geschäftsjahres."""

    op.execute("PRAGMA foreign_keys=OFF")

    op.create_table(
        "_wirtschaftsjahre_downgrade",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "mandant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO _wirtschaftsjahre_downgrade (
            id,
            mandant_id,
            start_date,
            end_date,
            status
        )
        SELECT
            id,
            mandant_id,
            start_date,
            end_date,
            status
        FROM wirtschaftsjahre
        """
    )

    op.drop_table("wirtschaftsjahre")

    op.rename_table(
        "_wirtschaftsjahre_downgrade",
        "wirtschaftsjahre",
    )

    op.execute("PRAGMA foreign_keys=ON")
