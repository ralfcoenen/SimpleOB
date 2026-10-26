"""allow multiple invoice open-item allocations per payment

Revision ID: cf6b9217da40
Revises: a3e4c7f61b20
Create Date: 2026-10-26 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "cf6b9217da40"
down_revision: Union[str, Sequence[str], None] = "a3e4c7f61b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "rechnungs_op_zahlungsereignisse"
_PAYMENT_ID_INDEX = "ix_rechnungs_op_zahlungsereignisse_payment_id"


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        with op.batch_alter_table(
            _TABLE,
            naming_convention={
                "uq": "uq_%(table_name)s_%(column_0_name)s",
            },
        ) as batch_op:
            batch_op.drop_constraint(
                "uq_rechnungs_op_zahlungsereignisse_payment_id",
                type_="unique",
            )
    else:
        inspector = sa.inspect(connection)
        payment_unique = next(
            constraint
            for constraint in inspector.get_unique_constraints(_TABLE)
            if constraint["column_names"] == ["payment_id"]
        )
        op.drop_constraint(payment_unique["name"], _TABLE, type_="unique")
    op.create_index(_PAYMENT_ID_INDEX, _TABLE, ["payment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(_PAYMENT_ID_INDEX, table_name=_TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.create_unique_constraint(None, ["payment_id"])
