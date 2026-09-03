"""add shareholders

Revision ID: 60a14109a8df
Revises: be557e4d89dd
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60a14109a8df"
down_revision: str | Sequence[str] | None = "be557e4d89dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Legt die Gesellschaftertabelle an."""

    op.create_table(
        "gesellschafter",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "shareholder_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "mandant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "shareholder_number",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "first_name",
            sa.String(),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "legal_status",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "share_numerator",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "share_denominator",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "tax_number",
            sa.String(),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "tax_id",
            sa.String(),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "wid",
            sa.String(),
            server_default="",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "shareholder_number",
            name=(
                "uq_gesellschafter_mandant_"
                "shareholder_number"
            ),
        ),
        sa.UniqueConstraint(
            "shareholder_id",
        ),
    )


def downgrade() -> None:
    """Entfernt die Gesellschaftertabelle."""

    op.drop_table(
        "gesellschafter",
    )
