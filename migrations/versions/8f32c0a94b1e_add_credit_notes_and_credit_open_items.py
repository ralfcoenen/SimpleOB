"""add customer and supplier credit notes with credit open items

Revision ID: 8f32c0a94b1e
Revises: 7c1f88e4d593
Create Date: 2026-10-26 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8f32c0a94b1e"
down_revision: Union[str, Sequence[str], None] = "7c1f88e4d593"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gutschriften",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_note_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("credit_note_kind", sa.String(length=16), nullable=False),
        sa.Column("note_number", sa.String(), nullable=False),
        sa.Column("note_date", sa.Date(), nullable=False),
        sa.Column(
            "original_receivable_invoice_id", sa.String(length=36), nullable=True
        ),
        sa.Column(
            "original_payable_invoice_id", sa.String(length=36), nullable=True
        ),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.Column("duplicate_reason", sa.String(), nullable=True),
        sa.CheckConstraint(
            "credit_note_kind IN ('CUSTOMER', 'SUPPLIER')",
            name="ck_gutschrift_art",
        ),
        sa.CheckConstraint(
            "NOT (original_receivable_invoice_id IS NOT NULL "
            "AND original_payable_invoice_id IS NOT NULL)",
            name="ck_gutschrift_nur_ein_rechnungsbezug",
        ),
        sa.CheckConstraint(
            "(credit_note_kind = 'CUSTOMER' AND original_payable_invoice_id IS NULL) "
            "OR (credit_note_kind = 'SUPPLIER' AND original_receivable_invoice_id IS NULL)",
            name="ck_gutschrift_rechnungsbezug_art",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_gutschrift_mandant_partner",
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["original_receivable_invoice_id"],
            ["ausgangsrechnungen.invoice_id"],
        ),
        sa.ForeignKeyConstraint(
            ["original_payable_invoice_id"],
            ["eingangsrechnungen.invoice_id"],
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id"),
        sa.UniqueConstraint("credit_note_id"),
    )
    op.create_table(
        "guthaben_ops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("open_item_id", sa.String(length=36), nullable=False),
        sa.Column("credit_note_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_guthaben_op_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["credit_note_id"], ["gutschriften.credit_note_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credit_note_id"),
        sa.UniqueConstraint("open_item_id"),
    )
    op.create_table(
        "guthaben_op_ereignisse",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("open_item_id", sa.String(length=36), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("amount_delta", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint(
            "amount_delta != 0",
            name="ck_guthaben_op_ereignis_betrag_ungleich_null",
        ),
        sa.ForeignKeyConstraint(
            ["open_item_id"], ["guthaben_ops.open_item_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("guthaben_op_ereignisse")
    op.drop_table("guthaben_ops")
    op.drop_table("gutschriften")
