"""add immutable payment allocation corrections

Revision ID: 7d0c4a28b9f1
Revises: 4b7f2a90c1de
Create Date: 2026-10-26 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7d0c4a28b9f1"
down_revision: Union[str, Sequence[str], None] = "4b7f2a90c1de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "zahlungszuordnungskorrekturen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correction_id", sa.String(length=36), nullable=False),
        sa.Column("mandant_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False),
        sa.Column("original_payment_id", sa.String(length=36), nullable=False),
        sa.Column("original_allocation_event_id", sa.String(length=36), nullable=False),
        sa.Column("source_receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("source_payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("target_receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("target_payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("correction_date", sa.Date(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("booking_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint(
            "(direction = 'CUSTOMER_RECEIPT' AND source_receivable_open_item_id IS NOT NULL "
            "AND source_payable_open_item_id IS NULL AND target_receivable_open_item_id IS NOT NULL "
            "AND target_payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER_PAYMENT' AND source_receivable_open_item_id IS NULL "
            "AND source_payable_open_item_id IS NOT NULL AND target_receivable_open_item_id IS NULL "
            "AND target_payable_open_item_id IS NOT NULL)",
            name="ck_zahlungszuordnungskorrektur_richtung_ops",
        ),
        sa.CheckConstraint(
            "direction IN ('CUSTOMER_RECEIPT', 'SUPPLIER_PAYMENT')",
            name="ck_zahlungszuordnungskorrektur_richtung",
        ),
        sa.CheckConstraint("amount > 0", name="ck_zahlungszuordnungskorrektur_betrag_positiv"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_zahlungszuordnungskorrektur_begruendung"),
        sa.CheckConstraint(
            "source_receivable_open_item_id IS NULL OR "
            "source_receivable_open_item_id != target_receivable_open_item_id",
            name="ck_zahlungszuordnungskorrektur_kundenziel_verschieden",
        ),
        sa.CheckConstraint(
            "source_payable_open_item_id IS NULL OR "
            "source_payable_open_item_id != target_payable_open_item_id",
            name="ck_zahlungszuordnungskorrektur_lieferantenziel_verschieden",
        ),
        sa.ForeignKeyConstraint(
            ["mandant_id", "partner_id"],
            ["geschaeftspartner.mandant_id", "geschaeftspartner.partner_id"],
            name="fk_zahlungszuordnungskorrektur_mandant_partner",
        ),
        sa.ForeignKeyConstraint(["mandant_id"], ["mandanten.id"]),
        sa.ForeignKeyConstraint(["original_payment_id"], ["zahlungen.payment_id"]),
        sa.ForeignKeyConstraint(
            ["original_allocation_event_id"],
            ["rechnungs_op_zahlungsereignisse.event_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["source_payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["target_receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["target_payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["buchungen.booking_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correction_id"),
        sa.UniqueConstraint("booking_id"),
    )
    op.create_index(
        "ix_zahlungszuordnungskorrekturen_original_allocation_event_id",
        "zahlungszuordnungskorrekturen",
        ["original_allocation_event_id"],
    )
    op.create_table(
        "zahlungszuordnungskorrekturereignisse",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("correction_id", sa.String(length=36), nullable=False),
        sa.Column("event_role", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False),
        sa.Column("receivable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("payable_open_item_id", sa.String(length=36), nullable=True),
        sa.Column("amount_delta", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "(direction = 'CUSTOMER_RECEIPT' AND receivable_open_item_id IS NOT NULL "
            "AND payable_open_item_id IS NULL) OR "
            "(direction = 'SUPPLIER_PAYMENT' AND receivable_open_item_id IS NULL "
            "AND payable_open_item_id IS NOT NULL)",
            name="ck_zahlungszuordnungskorrekturereignis_richtung_op",
        ),
        sa.CheckConstraint(
            "(event_role = 'SOURCE_RELEASE' AND amount_delta < 0) OR "
            "(event_role = 'TARGET_APPLY' AND amount_delta > 0)",
            name="ck_zahlungszuordnungskorrekturereignis_delta_richtung",
        ),
        sa.CheckConstraint(
            "event_role IN ('SOURCE_RELEASE', 'TARGET_APPLY')",
            name="ck_zahlungszuordnungskorrekturereignis_rolle",
        ),
        sa.CheckConstraint(
            "amount_delta != 0",
            name="ck_zahlungszuordnungskorrekturereignis_delta_nicht_null",
        ),
        sa.ForeignKeyConstraint(
            ["correction_id"], ["zahlungszuordnungskorrekturen.correction_id"]
        ),
        sa.ForeignKeyConstraint(
            ["receivable_open_item_id"], ["forderungs_ops.open_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["payable_open_item_id"], ["verbindlichkeits_ops.open_item_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint(
            "correction_id",
            "event_role",
            name="uq_zahlungszuordnungskorrekturereignis_korrektur_rolle",
        ),
    )
    op.create_index(
        "ix_zahlungszuordnungskorrekturereignisse_receivable_open_item_id",
        "zahlungszuordnungskorrekturereignisse",
        ["receivable_open_item_id"],
    )
    op.create_index(
        "ix_zahlungszuordnungskorrekturereignisse_payable_open_item_id",
        "zahlungszuordnungskorrekturereignisse",
        ["payable_open_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_zahlungszuordnungskorrekturereignisse_payable_open_item_id",
        table_name="zahlungszuordnungskorrekturereignisse",
    )
    op.drop_index(
        "ix_zahlungszuordnungskorrekturereignisse_receivable_open_item_id",
        table_name="zahlungszuordnungskorrekturereignisse",
    )
    op.drop_table("zahlungszuordnungskorrekturereignisse")
    op.drop_index(
        "ix_zahlungszuordnungskorrekturen_original_allocation_event_id",
        table_name="zahlungszuordnungskorrekturen",
    )
    op.drop_table("zahlungszuordnungskorrekturen")
