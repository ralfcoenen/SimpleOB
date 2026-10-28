"""add immutable credit open item refund reversals

Revision ID: c4e27a91b6d0
Revises: f2a91c7d5e30
Create Date: 2026-10-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e27a91b6d0"
down_revision: Union[str, Sequence[str], None] = "f2a91c7d5e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guthaben_op_rueckerstattungsruecknahmen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reversal_id", sa.String(length=36), nullable=False),
        sa.Column("refund_id", sa.String(length=36), nullable=False),
        sa.Column("reversal_booking_id", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_guthaben_op_ruecknahme_grund_nichtleer",
        ),
        sa.ForeignKeyConstraint(
            ["refund_id"],
            ["guthaben_op_rueckerstattungen.refund_id"],
            name="fk_guthaben_op_ruecknahme_refund",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_booking_id"],
            ["buchungen.booking_id"],
            name="fk_guthaben_op_ruecknahme_buchung",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reversal_id",
            name="uq_guthaben_op_ruecknahme_id",
        ),
        sa.UniqueConstraint(
            "refund_id",
            name="uq_guthaben_op_ruecknahme_refund",
        ),
        sa.UniqueConstraint(
            "reversal_booking_id",
            name="uq_guthaben_op_ruecknahme_buchung",
        ),
    )


def downgrade() -> None:
    op.drop_table("guthaben_op_rueckerstattungsruecknahmen")
