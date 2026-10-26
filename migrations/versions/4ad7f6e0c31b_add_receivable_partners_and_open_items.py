"""add business partners and receivable invoices/open items

Revision ID: 4ad7f6e0c31b
Revises: 3d5f3f742f56
Create Date: 2026-10-26 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4ad7f6e0c31b"
down_revision: Union[str, Sequence[str], None] = "3d5f3f742f56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geschaeftspartner",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_customer", sa.Boolean(), nullable=False),
        sa.Column("is_supplier", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "is_customer OR is_supplier",
            name="ck_geschaeftspartner_mindestens_eine_rolle",
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mandant_id",
            "partner_id",
            name="uq_geschaeftspartner_mandant_partner",
        ),
    )
    op.create_table(
        "ausgangsrechnungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_number", sa.String(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint(
            "gross_amount > 0",
            name="ck_ausgangsrechnung_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["buchungen.booking_id"]
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_ausgangsrechnung_mandant_partner",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id"),
        sa.UniqueConstraint("invoice_id"),
        sa.UniqueConstraint(
            "mandant_id",
            "invoice_number",
            name="uq_ausgangsrechnung_mandant_nummer",
        ),
    )
    op.create_table(
        "forderungs_ops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("open_item_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_forderungs_op_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["ausgangsrechnungen.invoice_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
        sa.UniqueConstraint("open_item_id"),
    )


def downgrade() -> None:
    op.drop_table("forderungs_ops")
    op.drop_table("ausgangsrechnungen")
    op.drop_table("geschaeftspartner")
