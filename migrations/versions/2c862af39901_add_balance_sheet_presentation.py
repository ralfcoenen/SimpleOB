"""add per-fiscal-year balance sheet presentation

Revision ID: 2c862af39901
Revises: f65c37865e28
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2c862af39901"
down_revision: Union[str, Sequence[str], None] = (
    "b7d41a8f2c60",
    "f2a91c7d5e30",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wirtschaftsjahre",
        sa.Column(
            "balance_sheet_presentation",
            sa.String(),
            nullable=False,
            server_default="A",
        ),
    )


def downgrade() -> None:
    op.drop_column("wirtschaftsjahre", "balance_sheet_presentation")
