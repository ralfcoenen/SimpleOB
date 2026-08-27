"""add vat configuration

Revision ID: ef72c557dbe1
Revises: 329033b53fb2
Create Date: 2026-08-27 08:58:01.859040

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef72c557dbe1"
down_revision: Union[str, Sequence[str], None] = (
    "329033b53fb2"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Umsatzsteuerkonfiguration je Mandant ergänzen."""

    op.create_table(
        "umsatzsteuer_konfiguration",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "mandant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "taxation_type",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "effective_from",
            sa.Date(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mandant_id"),
    )

    connection = op.get_bind()

    existing_companies = connection.execute(
        sa.text(
            """
            SELECT
                m.id AS mandant_id,
                MIN(w.start_date) AS effective_from
            FROM mandanten AS m
            JOIN wirtschaftsjahre AS w
                ON w.mandant_id = m.id
            GROUP BY m.id
            """
        )
    )

    for row in existing_companies:
        connection.execute(
            sa.text(
                """
                INSERT INTO umsatzsteuer_konfiguration (
                    mandant_id,
                    taxation_type,
                    effective_from
                )
                VALUES (
                    :mandant_id,
                    :taxation_type,
                    :effective_from
                )
                """
            ),
            {
                "mandant_id": row.mandant_id,
                "taxation_type": "STANDARD",
                "effective_from": row.effective_from,
            },
        )


def downgrade() -> None:
    """Umsatzsteuerkonfiguration entfernen."""

    op.drop_table(
        "umsatzsteuer_konfiguration"
    )
