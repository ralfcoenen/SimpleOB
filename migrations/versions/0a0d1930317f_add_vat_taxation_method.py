"""add vat taxation method

Revision ID: 0a0d1930317f
Revises: 3f30caaab745
Create Date: 2026-08-29 10:36:31.128892

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0a0d1930317f'
down_revision: Union[str, Sequence[str], None] = '3f30caaab745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "umsatzsteuer_konfiguration",
        sa.Column(
            "taxation_method",
            sa.String(),
            nullable=False,
            server_default="AGREED",
        ),
    )

    with op.batch_alter_table(
        "umsatzsteuer_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "taxation_method",
            server_default=None,
        )

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "umsatzsteuer_konfiguration"
    ) as batch_op:
        batch_op.drop_column(
            "taxation_method"
        )
