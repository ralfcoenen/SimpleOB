"""add durable person account links

Revision ID: 2f8c41d7a6b3
Revises: 2c862af39901
Create Date: 2026-11-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2f8c41d7a6b3"
down_revision: Union[str, Sequence[str], None] = "2c862af39901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "personenkonto_zuordnungen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(length=5), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=8), nullable=False),
        sa.CheckConstraint(
            "role IN ('DEBITOR', 'KREDITOR')",
            name="ck_personenkonto_rolle",
        ),
        sa.CheckConstraint(
            "length(account_number) = 5 AND "
            "((role = 'DEBITOR' AND CAST(account_number AS INTEGER) BETWEEN 10000 AND 69999) "
            "OR (role = 'KREDITOR' AND CAST(account_number AS INTEGER) BETWEEN 70000 AND 99999))",
            name="ck_personenkonto_nummernkreis",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "account_number"],
            ["konten.mandant_id", "konten.account_number"],
            name="fk_personenkonto_mandant_konto",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_personenkonto_mandant_partner",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mandant_id", "account_number",
            name="uq_personenkonto_mandant_konto",
        ),
        sa.UniqueConstraint(
            "mandant_id", "partner_id", "role",
            name="uq_personenkonto_mandant_partner_rolle",
        ),
    )


def downgrade() -> None:
    op.drop_table("personenkonto_zuordnungen")
