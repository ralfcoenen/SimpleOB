"""add equity contribution evidence

Revision ID: aaf27bdaaea3
Revises: eccb0d66e425
Create Date: 2026-09-29 17:03:32.909190

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aaf27bdaaea3"
down_revision: Union[str, Sequence[str], None] = "eccb0d66e425"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create equity contribution evidence."""

    op.create_table(
        "eigenkapitaleinlagen",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "buchungszeile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["buchungszeile_id"],
            ["buchungszeilen.id"],
        ),
        sa.UniqueConstraint(
            "buchungszeile_id",
        ),
    )


def downgrade() -> None:
    """Drop equity contribution evidence."""

    op.drop_table(
        "eigenkapitaleinlagen"
    )
