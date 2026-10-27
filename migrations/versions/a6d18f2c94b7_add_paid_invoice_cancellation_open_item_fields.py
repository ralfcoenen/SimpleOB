"""add paid invoice cancellation and alternate credit open item source

Revision ID: a6d18f2c94b7
Revises: d4a2f19c7b60
Create Date: 2026-10-27 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6d18f2c94b7"
down_revision: Union[str, Sequence[str], None] = "d4a2f19c7b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rechnungs_op_stornos",
        sa.Column("closed_open_amount", sa.Numeric(18, 2), nullable=True),
    )
    op.execute(
        "UPDATE rechnungs_op_stornos "
        "SET closed_open_amount = amount "
        "WHERE closed_open_amount IS NULL"
    )

    with op.batch_alter_table("rechnungs_op_stornos") as batch_op:
        batch_op.alter_column(
            "closed_open_amount",
            existing_type=sa.Numeric(18, 2),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_rechnungs_op_storno_schliessbetrag",
            "closed_open_amount >= 0 AND closed_open_amount <= amount",
        )
        batch_op.add_column(
            sa.Column("credit_booking_id", sa.String(36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_rechnungs_op_storno_credit_booking",
            "buchungen",
            ["credit_booking_id"],
            ["booking_id"],
        )
        batch_op.create_unique_constraint(
            "uq_rechnungs_op_storno_credit_buchung",
            ["credit_booking_id"],
        )

    with op.batch_alter_table("guthaben_ops") as batch_op:
        batch_op.alter_column(
            "credit_note_id",
            existing_type=sa.String(36),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("invoice_cancellation_id", sa.String(36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_guthaben_op_invoice_cancellation",
            "rechnungs_op_stornos",
            ["invoice_cancellation_id"],
            ["storno_id"],
        )
        batch_op.create_unique_constraint(
            "uq_guthaben_op_invoice_cancellation",
            ["invoice_cancellation_id"],
        )
        batch_op.create_check_constraint(
            "ck_guthaben_op_genau_eine_herkunft",
            "(credit_note_id IS NOT NULL AND invoice_cancellation_id IS NULL) OR "
            "(credit_note_id IS NULL AND invoice_cancellation_id IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("guthaben_ops") as batch_op:
        batch_op.drop_constraint(
            "ck_guthaben_op_genau_eine_herkunft", type_="check"
        )
        batch_op.drop_constraint(
            "uq_guthaben_op_invoice_cancellation", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_guthaben_op_invoice_cancellation", type_="foreignkey"
        )
        batch_op.drop_column("invoice_cancellation_id")
        batch_op.alter_column(
            "credit_note_id",
            existing_type=sa.String(36),
            nullable=False,
        )

    with op.batch_alter_table("rechnungs_op_stornos") as batch_op:
        batch_op.drop_constraint(
            "uq_rechnungs_op_storno_credit_buchung", type_="unique"
        )
        batch_op.drop_constraint(
            "fk_rechnungs_op_storno_credit_booking", type_="foreignkey"
        )
        batch_op.drop_column("credit_booking_id")
        batch_op.drop_constraint(
            "ck_rechnungs_op_storno_schliessbetrag", type_="check"
        )
        batch_op.drop_column("closed_open_amount")
