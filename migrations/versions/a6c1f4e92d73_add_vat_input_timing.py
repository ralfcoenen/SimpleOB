"""add vat input timing

Revision ID: a6c1f4e92d73
Revises: 84bd7378b310
Create Date: 2026-08-29

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "a6c1f4e92d73"
down_revision: str | None = "84bd7378b310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "umsatzsteuer_eingangsrechnungen",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "timing_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "buchung_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "service_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "invoice_received_date",
            sa.Date(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["buchung_id"],
            ["buchungen.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "timing_id",
            name="uq_umsatzsteuer_eingangsrechnungen_timing_id",
        ),
        sa.UniqueConstraint(
            "buchung_id",
            name="uq_umsatzsteuer_eingangsrechnungen_buchung_id",
        ),
    )

    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            """
            SELECT DISTINCT
                b.id AS buchung_id,
                b.booking_date AS booking_date
            FROM buchungen AS b
            JOIN umsatzsteuer_buchungsdetail AS d
              ON d.buchung_id = b.id
            WHERE d.direction = 'INPUT'
            """
        )
    ).mappings()

    for row in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO umsatzsteuer_eingangsrechnungen (
                    timing_id,
                    buchung_id,
                    service_date,
                    invoice_received_date
                )
                VALUES (
                    :timing_id,
                    :buchung_id,
                    :service_date,
                    :invoice_received_date
                )
                """
            ),
            {
                "timing_id": str(uuid4()),
                "buchung_id": row["buchung_id"],
                "service_date": row["booking_date"],
                "invoice_received_date": row["booking_date"],
            },
        )


def downgrade() -> None:
    op.drop_table(
        "umsatzsteuer_eingangsrechnungen"
    )
