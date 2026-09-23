"""add profit appropriation annual data

Revision ID: 603a8708b645
Revises: 5933da658a18
Create Date: 2026-09-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "603a8708b645"
down_revision: Union[str, Sequence[str], None] = "5933da658a18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gewinnverwendungs_jahresdaten",
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
            "statutory_reserve",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "other_revenue_reserves",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "distribution",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "profit_loss_carryforward",
            sa.Numeric(precision=18, scale=2),
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
        "gewinnverwendungs_jahresdaten"
    )
