"""add tax depreciation adjustments

Revision ID: 0bb446b0ceef
Revises: afeebc6f521a
Create Date: 2026-09-07 22:24:11.337671

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0bb446b0ceef'
down_revision: Union[str, Sequence[str], None] = 'afeebc6f521a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "steuerliche_afa_abweichungen",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "anlageabschreibung_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "tax_amount",
            sa.Numeric(
                precision=15,
                scale=2,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["anlageabschreibung_id"],
            ["anlageabschreibungen.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "anlageabschreibung_id",
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "steuerliche_afa_abweichungen"
    )
