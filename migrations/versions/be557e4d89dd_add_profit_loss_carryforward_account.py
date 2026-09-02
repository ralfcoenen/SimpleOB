"""add profit loss carryforward account

Revision ID: be557e4d89dd
Revises: 9f32dd1bb4a2
Create Date: 2026-09-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be557e4d89dd"
down_revision: Union[str, Sequence[str], None] = "9f32dd1bb4a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ergänzt das Konto für Gewinn-/Verlustvorträge."""

    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "profit_loss_carryforward_account",
            sa.String(),
            nullable=False,
            server_default="2970",
        ),
    )


def downgrade() -> None:
    """Entfernt das Konto für Gewinn-/Verlustvorträge."""

    op.drop_column(
        "kontenrahmen_konfiguration",
        "profit_loss_carryforward_account",
    )
