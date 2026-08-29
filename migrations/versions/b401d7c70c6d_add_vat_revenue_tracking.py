"""add vat revenue tracking

Revision ID: b401d7c70c6d
Revises: ef72c557dbe1
Create Date: 2026-08-27 14:30:49.345700

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b401d7c70c6d"
down_revision: Union[str, Sequence[str], None] = (
    "ef72c557dbe1"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """USt-Ausgangsumsätze und Zahlungszuordnungen ergänzen."""

    op.create_table(
        "umsatzsteuer_ausgangsumsatz",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "revenue_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "buchung_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "gross_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "revenue_kind",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "payment_kind",
            sa.String(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["buchung_id"],
            ["buchungen.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buchung_id"),
        sa.UniqueConstraint("revenue_id"),
    )

    op.create_table(
        "umsatzsteuer_zahlungszuordnung",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "allocation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "ausgangsumsatz_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "zahlungsbuchung_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ausgangsumsatz_id"],
            ["umsatzsteuer_ausgangsumsatz.id"],
        ),
        sa.ForeignKeyConstraint(
            ["zahlungsbuchung_id"],
            ["buchungen.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id"),
    )


def downgrade() -> None:
    """USt-Ausgangsumsätze und Zahlungszuordnungen entfernen."""

    op.drop_table(
        "umsatzsteuer_zahlungszuordnung"
    )
    op.drop_table(
        "umsatzsteuer_ausgangsumsatz"
    )
