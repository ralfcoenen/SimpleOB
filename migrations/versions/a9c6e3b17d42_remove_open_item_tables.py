"""remove legacy open-item tables

Revision ID: a9c6e3b17d42
Revises: 2f8c41d7a6b3
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a9c6e3b17d42"
down_revision: Union[str, Sequence[str], None] = "2f8c41d7a6b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES_TO_DROP = (
    "zahlungszuordnungskorrekturereignisse",
    "zahlungszuordnungskorrekturen",
    "rechnungs_op_zahlungsereignisse",
    "rechnungs_op_verrechnungsereignisse",
    "guthaben_op_ereignisse",
    "guthaben_op_rueckerstattungsruecknahmen",
    "guthaben_op_rueckerstattungen",
    "op_guthabenverrechnungen",
    "zahlungen",
    "guthaben_ops",
    "rechnungs_op_stornos",
    "forderungs_ops",
    "verbindlichkeits_ops",
    "gutschriften",
    "ausgangsrechnungen",
    "eingangsrechnungen",
)


def upgrade() -> None:
    """Entfernt ausschließlich die nicht mehr verwendete OP-Metadatenstruktur."""
    for table_name in _TABLES_TO_DROP:
        op.drop_table(table_name)


def downgrade() -> None:
    """Verweigert eine vorgetäuschte Wiederherstellung gelöschter OP-Daten."""
    raise RuntimeError(
        "Die OP-Tabellenmigration ist irreversibel. Eine Wiederherstellung "
        "ist nur aus einer vor der Migration erstellten Datenbanksicherung möglich."
    )
