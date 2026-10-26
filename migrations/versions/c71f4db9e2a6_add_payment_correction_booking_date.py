"""persist explicit booking date for payment allocation corrections

Revision ID: c71f4db9e2a6
Revises: 7d0c4a28b9f1
Create Date: 2026-10-26 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c71f4db9e2a6"
down_revision: Union[str, Sequence[str], None] = "7d0c4a28b9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "zahlungszuordnungskorrekturen",
        sa.Column("booking_date", sa.Date(), nullable=True),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE zahlungszuordnungskorrekturen "
            "SET booking_date = ("
            "SELECT buchungen.booking_date FROM buchungen "
            "WHERE buchungen.booking_id = "
            "zahlungszuordnungskorrekturen.booking_id) "
            "WHERE booking_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("zahlungszuordnungskorrekturen") as batch_op:
        batch_op.drop_column("booking_date")
