"""Add depreciation expense control account

Revision ID: 9981df44e390
Revises: e208ae74c789
Create Date: 2026-09-09 13:35:45.558774

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9981df44e390'
down_revision: Union[str, Sequence[str], None] = 'e208ae74c789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "depreciation_expense_account",
            sa.String(),
            nullable=False,
            server_default="4830",
        ),
    )

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "depreciation_expense_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.drop_column(
            "depreciation_expense_account"
        )
