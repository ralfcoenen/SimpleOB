"""add fixed asset disposal control accounts

Revision ID: 5933da658a18
Revises: 0f8a714038fd
Create Date: 2026-09-20 18:23:06.409181

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5933da658a18"
down_revision: Union[str, Sequence[str], None] = "0f8a714038fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "fixed_asset_disposal_gain_account",
            sa.String(),
            nullable=False,
            server_default="8500",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "fixed_asset_disposal_loss_account",
            sa.String(),
            nullable=False,
            server_default="4900",
        ),
    )

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "fixed_asset_disposal_gain_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "fixed_asset_disposal_loss_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.drop_column(
            "fixed_asset_disposal_loss_account"
        )
        batch_op.drop_column(
            "fixed_asset_disposal_gain_account"
        )
