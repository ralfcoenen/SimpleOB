"""add vat accounts to chart of accounts configuration

Revision ID: 43399f7117af
Revises: b0bd20e380ab
Create Date: 2026-08-20 12:27:44.490899

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "43399f7117af"
down_revision: Union[str, Sequence[str], None] = "b0bd20e380ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "input_tax_7",
            sa.String(),
            nullable=False,
            server_default="1571",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "input_tax_19",
            sa.String(),
            nullable=False,
            server_default="1576",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "output_tax_7",
            sa.String(),
            nullable=False,
            server_default="1771",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "output_tax_19",
            sa.String(),
            nullable=False,
            server_default="1776",
        ),
    )

    connection = op.get_bind()

    configuration_table = sa.table(
        "kontenrahmen_konfiguration",
        sa.column("mandant_id", sa.Integer()),
    )

    account_table = sa.table(
        "konten",
        sa.column("mandant_id", sa.Integer()),
        sa.column("account_number", sa.String()),
        sa.column("name", sa.String()),
        sa.column("account_type", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("debit_position_code", sa.String()),
        sa.column("credit_position_code", sa.String()),
    )

    company_ids = connection.execute(
        sa.select(configuration_table.c.mandant_id)
    ).scalars()

    standard_vat_accounts = (
        {
            "account_number": "1571",
            "name": "Abziehbare Vorsteuer 7 %",
            "account_type": "ASSET",
            "is_active": True,
            "debit_position_code": "HGB.266.AKTIVA.B.II.4",
            "credit_position_code": None,
        },
        {
            "account_number": "1576",
            "name": "Abziehbare Vorsteuer 19 %",
            "account_type": "ASSET",
            "is_active": True,
            "debit_position_code": "HGB.266.AKTIVA.B.II.4",
            "credit_position_code": None,
        },
        {
            "account_number": "1771",
            "name": "Umsatzsteuer 7 %",
            "account_type": "LIABILITY",
            "is_active": True,
            "debit_position_code": None,
            "credit_position_code": "HGB.266.PASSIVA.C.8",
        },
        {
            "account_number": "1776",
            "name": "Umsatzsteuer 19 %",
            "account_type": "LIABILITY",
            "is_active": True,
            "debit_position_code": None,
            "credit_position_code": "HGB.266.PASSIVA.C.8",
        },
    )

    for company_id in company_ids:
        for vat_account in standard_vat_accounts:
            account_number = vat_account["account_number"]

            existing_account = connection.execute(
                sa.select(
                    account_table.c.account_number,
                    account_table.c.account_type,
                    account_table.c.debit_position_code,
                    account_table.c.credit_position_code,
                ).where(
                    account_table.c.mandant_id == company_id,
                    account_table.c.account_number == account_number,
                )
            ).mappings().one_or_none()

            if existing_account is None:
                connection.execute(
                    account_table.insert().values(
                        mandant_id=company_id,
                        **vat_account,
                    )
                )
                continue

            if (
                existing_account["account_type"]
                != vat_account["account_type"]
                or existing_account["debit_position_code"]
                != vat_account["debit_position_code"]
                or existing_account["credit_position_code"]
                != vat_account["credit_position_code"]
            ):
                raise RuntimeError(
                    "Umsatzsteuerkonto kollidiert mit einem "
                    "vorhandenen Konto: "
                    f"Mandant {company_id}, Konto "
                    f"{account_number}."
                )

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "input_tax_7",
            server_default=None,
        )
        batch_op.alter_column(
            "input_tax_19",
            server_default=None,
        )
        batch_op.alter_column(
            "output_tax_7",
            server_default=None,
        )
        batch_op.alter_column(
            "output_tax_19",
            server_default=None,
        )


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.drop_column("output_tax_19")
        batch_op.drop_column("output_tax_7")
        batch_op.drop_column("input_tax_19")
        batch_op.drop_column("input_tax_7")
