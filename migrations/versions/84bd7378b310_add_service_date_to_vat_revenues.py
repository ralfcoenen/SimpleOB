"""add service date to vat revenues

Revision ID: 84bd7378b310
Revises: 0a0d1930317f
Create Date: 2026-08-29 17:56:18.133637

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '84bd7378b310'
down_revision: Union[str, Sequence[str], None] = '0a0d1930317f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "umsatzsteuer_ausgangsumsatz",
        sa.Column(
            "service_date",
            sa.Date(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE umsatzsteuer_ausgangsumsatz
        SET service_date = (
            SELECT booking_date
            FROM buchungen
            WHERE buchungen.id =
                umsatzsteuer_ausgangsumsatz.buchung_id
        )
        """
    )

    with op.batch_alter_table(
        "umsatzsteuer_ausgangsumsatz"
    ) as batch_op:
        batch_op.alter_column(
            "service_date",
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "umsatzsteuer_ausgangsumsatz"
    ) as batch_op:
        batch_op.drop_column("service_date")
