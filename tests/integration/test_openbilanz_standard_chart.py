"""Integrationstest für den OpenBilanz-Standardkontenrahmen."""

from pathlib import Path

from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)

STANDARD_CHART_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "openbilanz"
    / "resources"
    / "chart_of_accounts"
    / "openbilanz_standard.csv"
)


def test_imports_complete_openbilanz_standard_chart() -> None:
    """Der Standardkontenrahmen enthält Bilanz- und GuV-Zuordnungen."""

    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement,
        )
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(
        STANDARD_CHART_PATH
    )

    assert template.name == "openbilanz_standard"
    assert len(template.accounts) == 32
    assert len(template.account_mapping_rules) == 30

    accounts = {
        account.account_number: account
        for account in template.accounts
    }

    assert accounts["0400"].account_type is AccountType.ASSET
    assert accounts["0800"].account_type is AccountType.EQUITY
    assert accounts["1600"].account_type is AccountType.LIABILITY
    assert accounts["4830"].account_type is AccountType.EXPENSE
    assert accounts["8400"].account_type is AccountType.REVENUE

    rules = {
        rule.account_number: rule
        for rule in template.account_mapping_rules
    }

    assert (
        rules["0400"].debit_position.code
        == "HGB.266.AKTIVA.A.II.3"
    )

    assert (
        rules["0800"].credit_position.code
        == "HGB.266.PASSIVA.A.I"
    )

    assert (
        rules["1400"].debit_position.code
        == "HGB.266.AKTIVA.B.II.1"
    )

    assert (
        rules["1600"].credit_position.code
        == "HGB.266.PASSIVA.C.4"
    )

    assert (
        rules["4830"].debit_position.code
        == "HGB.275.GKV.7.a"
    )

    assert (
        rules["8400"].credit_position.code
        == "HGB.275.GKV.1"
    )
