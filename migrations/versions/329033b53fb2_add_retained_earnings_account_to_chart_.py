"""add retained earnings account to chart configuration

Revision ID: 329033b53fb2
Revises: 9f32dd1bb4a2
Create Date: 2026-08-26 16:29:53.106025

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '329033b53fb2'
down_revision: Union[str, Sequence[str], None] = '9f32dd1bb4a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "retained_earnings_account",
            sa.String(),
            nullable=False,
            server_default="2970",
        ),
    )

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "retained_earnings_account",
            server_default=None,
        )


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.drop_column(
            "retained_earnings_account"
        )
