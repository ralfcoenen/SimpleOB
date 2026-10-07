"""add account taxonomy mappings

Revision ID: 3d5f3f742f56
Revises: f65c37865e28
Create Date: 2026-10-07 21:20:18.972810
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3d5f3f742f56"
down_revision: Union[str, Sequence[str], None] = "f65c37865e28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "konten_taxonomie_zuordnungen"


def upgrade() -> None:
    """Ergänzt die fehlende Persistenz für Konten-Taxonomiezuordnungen."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
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
            "account_number",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "taxonomy_version",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "concept_name",
            sa.String(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id"],
            ["mandanten.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "mandant_id",
            "account_number",
            "taxonomy_version",
            name=(
                "uq_konten_taxonomie_"
                "mandant_account_version"
            ),
        ),
    )


def downgrade() -> None:
    """Entfernt die Persistenz für Konten-Taxonomiezuordnungen."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
