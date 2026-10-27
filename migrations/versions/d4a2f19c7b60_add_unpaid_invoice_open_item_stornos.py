"""add full storno records for unpaid invoice open items

Revision ID: d4a2f19c7b60
Revises: c71f4db9e2a6
Create Date: 2026-10-26 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a2f19c7b60"
down_revision: Union[str, Sequence[str], None] = "c71f4db9e2a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rechnungs_op_stornos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storno_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("receivable_invoice_id", sa.String(length=36), nullable=True),
        sa.Column("payable_invoice_id", sa.String(length=36), nullable=True),
        sa.Column("receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.CheckConstraint(
            "(receivable_invoice_id IS NOT NULL "
            "AND receivable_open_item_id IS NOT NULL "
            "AND payable_invoice_id IS NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(receivable_invoice_id IS NULL "
            "AND receivable_open_item_id IS NULL "
            "AND payable_invoice_id IS NOT NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_rechnungs_op_storno_genau_eine_richtung",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_rechnungs_op_storno_betrag_positiv",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_rechnungs_op_storno_begruendung",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"], ["mandanten.id"],
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_rechnungs_op_storno_mandant_partner",
        ),
        sa.ForeignKeyConstraint(
            ["receivable_invoice_id"], ["ausgangsrechnungen.invoice_id"],
        ),
        sa.ForeignKeyConstraint(
            ["payable_invoice_id"], ["eingangsrechnungen.invoice_id"],
        ),
        sa.ForeignKeyConstraint(
            ["receivable_open_item_id"], ["forderungs_ops.open_item_id"],
        ),
        sa.ForeignKeyConstraint(
            ["payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"],
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storno_id"),
        sa.UniqueConstraint(
            "receivable_invoice_id",
            name="uq_rechnungs_op_storno_ausgangsrechnung",
        ),
        sa.UniqueConstraint(
            "payable_invoice_id",
            name="uq_rechnungs_op_storno_eingangsrechnung",
        ),
        sa.UniqueConstraint(
            "receivable_open_item_id",
            name="uq_rechnungs_op_storno_forderungs_op",
        ),
        sa.UniqueConstraint(
            "payable_open_item_id",
            name="uq_rechnungs_op_storno_verbindlichkeits_op",
        ),
        sa.UniqueConstraint(
            "booking_id",
            name="uq_rechnungs_op_storno_buchung",
        ),
    )


def downgrade() -> None:
    op.drop_table("rechnungs_op_stornos")
