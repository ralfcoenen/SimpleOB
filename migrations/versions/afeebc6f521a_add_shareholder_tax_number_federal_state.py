"""add shareholder tax number federal state

Revision ID: afeebc6f521a
Revises: 60a14109a8df
Create Date: 2026-09-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afeebc6f521a"
down_revision: Union[str, None] = "60a14109a8df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ergänzt das Bundesland der Gesellschafter-Steuernummer."""

    op.add_column(
        "gesellschafter",
        sa.Column(
            "tax_number_federal_state",
            sa.String(),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    """Entfernt das Bundesland der Gesellschafter-Steuernummer."""

    op.drop_column(
        "gesellschafter",
        "tax_number_federal_state",
    )
