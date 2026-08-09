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


def test_imports_openbilanz_standard_chart_of_accounts() -> None:
    csv_file = Path(
        "src/openbilanz/resources/chart_of_accounts/openbilanz_standard.csv"
    )

    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement,
        ),
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    assert template.name == "openbilanz_standard"

    assert len(template.accounts) == 11
    assert len(template.account_mapping_rules) == 11

    bank = next(
        account
        for account in template.accounts
        if account.account_number == "1200"
    )
    revenue = next(
        account
        for account in template.accounts
        if account.account_number == "8400"
    )

    assert bank.name == "Bank"
    assert bank.account_type is AccountType.ASSET

    assert revenue.name == "Umsatzerlöse"
    assert revenue.account_type is AccountType.REVENUE

    bank_rule = next(
        rule
        for rule in template.account_mapping_rules
        if rule.account_number == "1200"
    )
    revenue_rule = next(
        rule
        for rule in template.account_mapping_rules
        if rule.account_number == "8400"
    )

    assert bank_rule.debit_position is not None
    assert bank_rule.debit_position.code == "HGB.266.AKTIVA.B.IV"

    assert revenue_rule.credit_position is not None
    assert revenue_rule.credit_position.code == "HGB.275.GKV.1"
    
    