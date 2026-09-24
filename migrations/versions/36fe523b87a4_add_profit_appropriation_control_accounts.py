"""add profit appropriation control accounts

Revision ID: 36fe523b87a4
Revises: d6043facfad4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "36fe523b87a4"
down_revision: Union[str, Sequence[str], None] = "d6043facfad4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_ACCOUNTS = (
    {
        "account_number": "0755",
        "name": (
            "Verbindlichkeiten gegenüber Gesellschaftern "
            "für offene Ausschüttungen"
        ),
        "account_type": "LIABILITY",
        "debit_position_code": None,
        "credit_position_code": "HGB.266.PASSIVA.C.8",
    },
    {
        "account_number": "0846",
        "name": "Gesetzliche Rücklage",
        "account_type": "EQUITY",
        "debit_position_code": None,
        "credit_position_code": "HGB.266.PASSIVA.A.III.1",
    },
    {
        "account_number": "0855",
        "name": "Andere Gewinnrücklagen",
        "account_type": "EQUITY",
        "debit_position_code": None,
        "credit_position_code": "HGB.266.PASSIVA.A.III.4",
    },
)


def upgrade() -> None:
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "statutory_reserve_account",
            sa.String(),
            nullable=False,
            server_default="0846",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "other_revenue_reserves_account",
            sa.String(),
            nullable=False,
            server_default="0855",
        ),
    )
    op.add_column(
        "kontenrahmen_konfiguration",
        sa.Column(
            "distribution_liability_account",
            sa.String(),
            nullable=False,
            server_default="0755",
        ),
    )

    connection = op.get_bind()

    company_ids = connection.execute(
        sa.text(
            """
            SELECT id
            FROM mandanten
            """
        )
    ).scalars()

    for company_id in company_ids:
        for account in _NEW_ACCOUNTS:
            exists = connection.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM konten
                    WHERE mandant_id = :mandant_id
                      AND account_number = :account_number
                    LIMIT 1
                    """
                ),
                {
                    "mandant_id": company_id,
                    "account_number": account["account_number"],
                },
            ).first()

            if exists is not None:
                continue

            connection.execute(
                sa.text(
                    """
                    INSERT INTO konten (
                        mandant_id,
                        account_number,
                        name,
                        account_type,
                        is_active,
                        debit_position_code,
                        credit_position_code
                    )
                    VALUES (
                        :mandant_id,
                        :account_number,
                        :name,
                        :account_type,
                        :is_active,
                        :debit_position_code,
                        :credit_position_code
                    )
                    """
                ),
                {
                    "mandant_id": company_id,
                    "account_number": account["account_number"],
                    "name": account["name"],
                    "account_type": account["account_type"],
                    "is_active": True,
                    "debit_position_code": account[
                        "debit_position_code"
                    ],
                    "credit_position_code": account[
                        "credit_position_code"
                    ],
                },
            )

    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.alter_column(
            "statutory_reserve_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "other_revenue_reserves_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "distribution_liability_account",
            existing_type=sa.String(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "kontenrahmen_konfiguration"
    ) as batch_op:
        batch_op.drop_column(
            "distribution_liability_account"
        )
        batch_op.drop_column(
            "other_revenue_reserves_account"
        )
        batch_op.drop_column(
            "statutory_reserve_account"
        )
