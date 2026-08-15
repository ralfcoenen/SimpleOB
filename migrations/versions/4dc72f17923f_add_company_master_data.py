"""add company master data

Revision ID: 4dc72f17923f
Revises: 4a10212b0bd0
Create Date: 2026-08-14 16:17:25.915444

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4dc72f17923f'
down_revision: Union[str, Sequence[str], None] = '4a10212b0bd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mandanten",
        sa.Column(
            "steuer_id",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "wirtschafts_id",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "bf4",
            sa.String(length=4),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "strasse",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "hausnummer",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "plz",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "ort",
            sa.String(),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "land",
            sa.String(length=2),
            nullable=True,
        ),
    )

    op.add_column(
        "mandanten",
        sa.Column(
            "geschaeftstaetigkeit",
            sa.String(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "mandanten",
        "geschaeftstaetigkeit",
    )
    op.drop_column(
        "mandanten",
        "land",
    )
    op.drop_column(
        "mandanten",
        "ort",
    )
    op.drop_column(
        "mandanten",
        "plz",
    )
    op.drop_column(
        "mandanten",
        "hausnummer",
    )
    op.drop_column(
        "mandanten",
        "strasse",
    )
    op.drop_column(
        "mandanten",
        "bf4",
    )
    op.drop_column(
        "mandanten",
        "wirtschafts_id",
    )
    op.drop_column(
        "mandanten",
        "steuer_id",
    )
    