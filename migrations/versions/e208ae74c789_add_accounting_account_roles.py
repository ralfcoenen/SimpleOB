"""add accounting account roles

Revision ID: e208ae74c789
Revises: 0bb446b0ceef
Create Date: 2026-09-09 08:50:47.078670
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e208ae74c789"
down_revision: Union[str, Sequence[str], None] = (
    "0bb446b0ceef"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "kontenrollen",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "mandant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "account_number",
            sa.String(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "account_number",
            name="uq_kontenrollen_mandant_account",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table(
        "kontenrollen"
    )
