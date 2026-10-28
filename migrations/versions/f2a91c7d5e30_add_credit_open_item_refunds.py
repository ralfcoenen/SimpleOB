"""add immutable credit open item refund movements

Revision ID: f2a91c7d5e30
Revises: a6d18f2c94b7
Create Date: 2026-10-27 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a91c7d5e30"
down_revision: Union[str, Sequence[str], None] = "a6d18f2c94b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guthaben_op_rueckerstattungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("refund_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("open_item_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("refund_date", sa.Date(), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "direction IN ('CUSTOMER', 'SUPPLIER')",
            name="ck_guthaben_op_refund_richtung",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_guthaben_op_refund_betrag_positiv",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_guthaben_op_refund_mandant_partner",
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(
            ["open_item_id"], ["guthaben_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "refund_id",
            name="uq_guthaben_op_refund_id",
        ),
        sa.UniqueConstraint(
            "booking_id",
            name="uq_guthaben_op_refund_booking",
        ),
    )
    op.create_index(
        "ix_guthaben_op_refund_open_item",
        "guthaben_op_rueckerstattungen",
        ["open_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_guthaben_op_refund_open_item",
        table_name="guthaben_op_rueckerstattungen",
    )
    op.drop_table("guthaben_op_rueckerstattungen")
