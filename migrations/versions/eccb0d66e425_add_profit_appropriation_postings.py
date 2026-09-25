"""add profit appropriation postings

Revision ID: eccb0d66e425
Revises: 36fe523b87a4
Create Date: 2026-09-25 10:11:52.804199

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "eccb0d66e425"
down_revision: Union[str, Sequence[str], None] = "36fe523b87a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create profit appropriation posting evidence."""

    op.create_table(
        "gewinnverwendungsbuchungen",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "posting_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "quell_wirtschaftsjahr_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "buchungszeile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "posting_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "posting_type",
            sa.String(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["quell_wirtschaftsjahr_id"],
            ["wirtschaftsjahre.id"],
        ),
        sa.ForeignKeyConstraint(
            ["buchungszeile_id"],
            ["buchungszeilen.id"],
        ),
        sa.UniqueConstraint(
            "posting_id",
        ),
        sa.UniqueConstraint(
            "buchungszeile_id",
        ),
    )


def downgrade() -> None:
    """Drop profit appropriation posting evidence."""

    op.drop_table(
        "gewinnverwendungsbuchungen"
    )
