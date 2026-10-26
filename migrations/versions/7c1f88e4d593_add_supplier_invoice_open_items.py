"""add supplier invoices and payable open items

Revision ID: 7c1f88e4d593
Revises: 4ad7f6e0c31b
Create Date: 2026-10-26 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c1f88e4d593"
down_revision: Union[str, Sequence[str], None] = "4ad7f6e0c31b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eingangsrechnungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_number", sa.String(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.Column("duplicate_reason", sa.String(), nullable=True),
        sa.CheckConstraint(
            "gross_amount > 0",
            name="ck_eingangsrechnung_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["buchungen.booking_id"]
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_eingangsrechnung_mandant_partner",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id"),
        sa.UniqueConstraint("invoice_id"),
    )
    op.create_table(
        "verbindlichkeits_ops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("open_item_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_verbindlichkeits_op_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["eingangsrechnungen.invoice_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
        sa.UniqueConstraint("open_item_id"),
    )


def downgrade() -> None:
    op.drop_table("verbindlichkeits_ops")
    op.drop_table("eingangsrechnungen")
