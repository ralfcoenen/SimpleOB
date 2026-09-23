"""extend profit appropriation annual data

Revision ID: d6043facfad4
Revises: 603a8708b645
Create Date: 2026-09-23 09:49:36.202251

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d6043facfad4"
down_revision: Union[str, Sequence[str], None] = "603a8708b645"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table(
        "gewinnverwendungs_jahresdaten"
    ) as batch_op:
        batch_op.alter_column(
            "statutory_reserve",
            new_column_name="statutory_reserve_addition",
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "other_revenue_reserves",
            new_column_name="other_revenue_reserves_addition",
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )
        batch_op.add_column(
            sa.Column(
                "statutory_reserve_release",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "other_revenue_reserves_release",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=False,
                server_default="0",
            )
        )

    with op.batch_alter_table(
        "gewinnverwendungs_jahresdaten"
    ) as batch_op:
        batch_op.alter_column(
            "statutory_reserve_release",
            server_default=None,
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "other_revenue_reserves_release",
            server_default=None,
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "gewinnverwendungs_jahresdaten"
    ) as batch_op:
        batch_op.drop_column(
            "other_revenue_reserves_release"
        )
        batch_op.drop_column(
            "statutory_reserve_release"
        )
        batch_op.alter_column(
            "other_revenue_reserves_addition",
            new_column_name="other_revenue_reserves",
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "statutory_reserve_addition",
            new_column_name="statutory_reserve",
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            existing_nullable=False,
        )
