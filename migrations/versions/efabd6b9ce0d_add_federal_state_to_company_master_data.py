"""add federal state to company master data

Revision ID: efabd6b9ce0d
Revises: 6a4d3aa58649
Create Date: 2026-08-15 16:52:08.592502
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "efabd6b9ce0d"
down_revision: Union[str, Sequence[str], None] = "6a4d3aa58649"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fügt das Bundesland zu den Unternehmensstammdaten hinzu."""

    op.add_column(
        "mandanten",
        sa.Column(
            "bundesland",
            sa.String(length=2),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Entfernt das Bundesland aus den Unternehmensstammdaten."""

    op.drop_column(
        "mandanten",
        "bundesland",
    )