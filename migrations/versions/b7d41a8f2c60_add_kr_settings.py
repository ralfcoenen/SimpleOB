"""add tenant KR settings and calendar-year turnover additions

Revision ID: b7d41a8f2c60
Revises: c4e27a91b6d0
Create Date: 2026-10-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d41a8f2c60"
down_revision: Union[str, Sequence[str], None] = "c4e27a91b6d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mandanten",
        sa.Column("taetigkeitsbeginn", sa.Date(), nullable=True),
    )
    op.add_column(
        "mandanten",
        sa.Column(
            "kr_verzicht",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "mandanten",
        sa.Column("kr_verzicht_datum", sa.Date(), nullable=True),
    )
    op.create_table(
        "kr_jahresumsatz_ergaenzungen",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("kalenderjahr", sa.Integer(), nullable=False),
        sa.Column(
            "betrag",
            sa.Numeric(18, 2),
            server_default="0.00",
            nullable=False,
        ),
        sa.CheckConstraint(
            "kalenderjahr >= 1 AND kalenderjahr <= 9999",
            name="ck_kr_jahresumsatz_kalenderjahr",
        ),
        sa.CheckConstraint(
            "betrag >= 0",
            name="ck_kr_jahresumsatz_betrag_nichtnegativ",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mandant_id",
            "kalenderjahr",
            name="uq_kr_jahresumsatz_mandant_jahr",
        ),
    )


def downgrade() -> None:
    op.drop_table("kr_jahresumsatz_ergaenzungen")
    op.drop_column("mandanten", "kr_verzicht_datum")
    op.drop_column("mandanten", "kr_verzicht")
    op.drop_column("mandanten", "taetigkeitsbeginn")
