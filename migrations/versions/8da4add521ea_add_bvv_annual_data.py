"""add bvv annual data

Revision ID: 8da4add521ea
Revises: 9981df44e390
Create Date: 2026-09-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8da4add521ea"
down_revision: Union[str, Sequence[str], None] = "9981df44e390"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bvv_jahresdaten",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "wirtschaftsjahr_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "previous_hgb_equity",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "contribution",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "withdrawal_distribution",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["wirtschaftsjahr_id"],
            ["wirtschaftsjahre.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "wirtschaftsjahr_id",
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "bvv_jahresdaten"
    )
