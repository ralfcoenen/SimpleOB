"""baseline v0.20.0

Revision ID: 7392d6cc6892
Revises:
Create Date: 2026-08-09 13:19:03.908336
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7392d6cc6892"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Erzeugt das Datenbankschema der Baseline v0.20.0."""

    op.create_table(
        "mandanten",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "rechtsform",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "steuernummer",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "finanzamt",
            sa.String(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )

    op.create_table(
        "wirtschaftsjahre",
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

    op.create_table(
        "buchungen",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "wirtschaftsjahr_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "booking_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "voucher_no",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.String(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["wirtschaftsjahr_id"],
            ["wirtschaftsjahre.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id"),
    )

    op.create_table(
        "buchungszeilen",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "buchung_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "account_number",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "side",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["buchung_id"],
            ["buchungen.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Entfernt das Datenbankschema der Baseline v0.20.0."""

    op.drop_table("buchungszeilen")
    op.drop_table("buchungen")
    op.drop_table("wirtschaftsjahre")
    op.drop_table("mandanten")