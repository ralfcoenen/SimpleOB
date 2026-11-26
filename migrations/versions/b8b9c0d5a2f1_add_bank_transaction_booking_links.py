"""Add unique links from imported bank transactions to bookings.

Revision ID: b8b9c0d5a2f1
Revises: a9c6e3b17d42
Create Date: 2026-11-25 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8b9c0d5a2f1"
down_revision: Union[str, Sequence[str], None] = "a9c6e3b17d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_transaction_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("import_source", sa.String(), nullable=False),
        sa.Column("external_transaction_id", sa.String(), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mandant_id",
            "import_source",
            "external_transaction_id",
            name="uq_bank_transaction_booking_external_id",
        ),
        sa.UniqueConstraint(
            "booking_id",
            name="uq_bank_transaction_booking_booking_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("bank_transaction_bookings")
