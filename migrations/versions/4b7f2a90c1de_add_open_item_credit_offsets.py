"""add manual offsets between credit and invoice open items

Revision ID: 4b7f2a90c1de
Revises: cf6b9217da40
Create Date: 2026-10-26 19:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4b7f2a90c1de"
down_revision: Union[str, Sequence[str], None] = "cf6b9217da40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "op_guthabenverrechnungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("credit_open_item_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint(
            "(direction = 'CUSTOMER' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_op_verrechnung_richtung_rechnungs_op",
        ),
        sa.CheckConstraint(
            "direction IN ('CUSTOMER', 'SUPPLIER')",
            name="ck_op_verrechnung_richtung",
        ),
        sa.CheckConstraint("amount > 0", name="ck_op_verrechnung_betrag_positiv"),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_op_verrechnung_mandant_partner",
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["credit_open_item_id"], ["guthaben_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_id"),
        sa.UniqueConstraint("booking_id"),
    )
    op.create_table(
        "rechnungs_op_verrechnungsereignisse",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("settlement_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "(direction = 'CUSTOMER' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_rechnungs_op_verrechnung_richtung_op",
        ),
        sa.CheckConstraint(
            "amount > 0", name="ck_rechnungs_op_verrechnung_betrag_positiv"
        ),
        sa.ForeignKeyConstraint(
            ["settlement_id"], ["op_guthabenverrechnungen.settlement_id"]
        ),
        sa.ForeignKeyConstraint(
            ["receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint(
            "settlement_id", name="uq_rechnungs_op_verrechnung_settlement"
        ),
    )
    with op.batch_alter_table("guthaben_op_ereignisse") as batch_op:
        batch_op.add_column(sa.Column("settlement_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_guthaben_op_ereignis_settlement",
            "op_guthabenverrechnungen",
            ["settlement_id"],
            ["settlement_id"],
        )
        batch_op.create_unique_constraint(
            "uq_guthaben_op_ereignisse_settlement", ["settlement_id"]
        )


def downgrade() -> None:
    op.drop_table("rechnungs_op_verrechnungsereignisse")
    with op.batch_alter_table("guthaben_op_ereignisse") as batch_op:
        batch_op.drop_constraint(
            "uq_guthaben_op_ereignisse_settlement", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_guthaben_op_ereignis_settlement", type_="foreignkey"
        )
        batch_op.drop_column("settlement_id")
    op.drop_table("op_guthabenverrechnungen")
