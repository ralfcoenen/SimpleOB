"""add booking reversal reference

Revision ID: 0f8a714038fd
Revises: 8da4add521ea
Create Date: 2026-09-13 12:36:43.185036

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0f8a714038fd"
down_revision: Union[str, Sequence[str], None] = "8da4add521ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "buchungen",
        sa.Column(
            "reversal_of_booking_id",
            sa.String(length=36),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "buchungen",
        "reversal_of_booking_id",
    )
