"""add booking type

Revision ID: 6a4d3aa58649
Revises: 4dc72f17923f
Create Date: 2026-08-15 14:52:03.194453
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a4d3aa58649"
down_revision: Union[str, Sequence[str], None] = "4dc72f17923f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fügt den fachlichen Buchungstyp hinzu."""

    op.add_column(
        "buchungen",
        sa.Column(
            "booking_type",
            sa.String(),
            server_default="REGULAR",
            nullable=False,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE buchungen
            SET booking_type = 'CLOSING'
            WHERE description LIKE 'Abschluss des Erlöskontos %'
               OR description LIKE 'Abschluss des Aufwandskontos %'
               OR description = 'Abschluss des GuV-Kontos'
            """
        )
    )


def downgrade() -> None:
    """Entfernt den fachlichen Buchungstyp."""

    op.drop_column(
        "buchungen",
        "booking_type",
    )
