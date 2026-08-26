"""add fixed asset movements

Revision ID: 9f32dd1bb4a2
Revises: 43399f7117af
Create Date: 2026-08-23 11:14:34.300457
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f32dd1bb4a2"
down_revision: Union[str, Sequence[str], None] = "43399f7117af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ergänzt persistierte Anlagenbewegungen."""

    op.create_table(
        "anlagebewegungen",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "movement_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "anlagegut_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "wirtschaftsjahr_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "buchungszeile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "movement_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "movement_type",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "reversed_movement_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["anlagegut_id"],
            ["anlagegueter.id"],
        ),
        sa.ForeignKeyConstraint(
            ["wirtschaftsjahr_id"],
            ["wirtschaftsjahre.id"],
        ),
        sa.ForeignKeyConstraint(
            ["buchungszeile_id"],
            ["buchungszeilen.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reversed_movement_id"],
            ["anlagebewegungen.id"],
        ),
        sa.UniqueConstraint(
            "movement_id",
            name="uq_anlagebewegungen_movement_id",
        ),
        sa.UniqueConstraint(
            "buchungszeile_id",
            name="uq_anlagebewegungen_buchungszeile_id",
        ),
        sa.UniqueConstraint(
            "reversed_movement_id",
            name="uq_anlagebewegungen_reversed_movement_id",
        ),
    )


def downgrade() -> None:
    """Entfernt persistierte Anlagenbewegungen."""

    op.drop_table(
        "anlagebewegungen"
    )
