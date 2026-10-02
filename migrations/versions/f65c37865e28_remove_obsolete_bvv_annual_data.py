"""remove obsolete bvv annual data

Revision ID: f65c37865e28
Revises: aaf27bdaaea3
Create Date: 2026-10-02 09:36:44.969642

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f65c37865e28"
down_revision: Union[str, Sequence[str], None] = "aaf27bdaaea3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Entfernt die nicht mehr benötigten BVV-Jahresdaten."""

    op.drop_table("bvv_jahresdaten")


def downgrade() -> None:
    """Stellt die frühere BVV-Jahresdatentabelle wieder her."""

    op.create_table(
        "bvv_jahresdaten",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "wirtschaftsjahr_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "previous_hgb_equity",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column(
            "contribution",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.Column(
            "withdrawal_distribution",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["wirtschaftsjahr_id"],
            ["wirtschaftsjahre.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wirtschaftsjahr_id"),
    )
