"""add payments and invoice open-item allocation events

Revision ID: a3e4c7f61b20
Revises: 8f32c0a94b1e
Create Date: 2026-10-26 16:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3e4c7f61b20"
down_revision: Union[str, Sequence[str], None] = "8f32c0a94b1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "zahlungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint(
            "direction IN ('CUSTOMER_RECEIPT', 'SUPPLIER_PAYMENT')",
            name="ck_zahlung_richtung",
        ),
        sa.CheckConstraint("amount > 0", name="ck_zahlung_betrag_positiv"),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_zahlung_mandant_partner",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id"),
        sa.UniqueConstraint("payment_id"),
    )
    op.create_table(
        "rechnungs_op_zahlungsereignisse",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False),
        sa.Column("receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "(direction = 'CUSTOMER_RECEIPT' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER_PAYMENT' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_rechnungs_op_zahlung_richtung_op",
        ),
        sa.CheckConstraint(
            "direction IN ('CUSTOMER_RECEIPT', 'SUPPLIER_PAYMENT')",
            name="ck_rechnungs_op_zahlung_richtung",
        ),
        sa.CheckConstraint(
            "amount > 0", name="ck_rechnungs_op_zahlung_betrag_positiv"
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["zahlungen.payment_id"]
        ),
        sa.ForeignKeyConstraint(
            ["receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("payment_id"),
    )


def downgrade() -> None:
    op.drop_table("rechnungs_op_zahlungsereignisse")
    op.drop_table("zahlungen")
