from pathlib import Path

from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.domain.account_type import AccountType
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)


def test_imports_openbilanz_standard_chart_of_accounts() -> None:
    csv_file = Path(
        "src/simpleob/resources/chart_of_accounts/openbilanz_standard.csv"
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

    account_numbers = {
        account.account_number
        for account in template.accounts
    }

    assert "1571" in account_numbers
    assert "1576" in account_numbers
    assert "1771" in account_numbers
    assert "1776" in account_numbers
    assert "8990" in account_numbers
    assert "9000" in account_numbers
    assert {"1400", "1410", "1600", "1610"} <= account_numbers

    assert len(account_numbers) == len(template.accounts)
    mapped_account_numbers = {
        rule.account_number
        for rule in template.account_mapping_rules
    }

    assert "1571" in mapped_account_numbers
    assert "1576" in mapped_account_numbers
    assert "1771" in mapped_account_numbers
    assert "1776" in mapped_account_numbers
    assert {"1400", "1410", "1600", "1610"} <= mapped_account_numbers

    assert len(mapped_account_numbers) == len(
        template.account_mapping_rules
    )

    assert "8990" not in mapped_account_numbers
    assert "9000" not in mapped_account_numbers

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

    assert revenue.name == "Umsatzerlöse 19 %"
    assert revenue.account_type is AccountType.REVENUE

    account_types = {
        account.account_number: account.account_type
        for account in template.accounts
    }
    assert account_types["1400"] is AccountType.ASSET
    assert account_types["1410"] is AccountType.ASSET
    assert account_types["1600"] is AccountType.LIABILITY
    assert account_types["1610"] is AccountType.LIABILITY

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

    expected_hgb_positions = {
        "1400": ("HGB.266.AKTIVA.B.II.1", None),
        "1410": ("HGB.266.AKTIVA.B.II.4", None),
        "1600": (None, "HGB.266.PASSIVA.C.4"),
        "1610": (None, "HGB.266.PASSIVA.C.8"),
    }
    rules_by_account_number = {
        rule.account_number: rule
        for rule in template.account_mapping_rules
    }
    for account_number, (debit_code, credit_code) in expected_hgb_positions.items():
        rule = rules_by_account_number[account_number]
        assert (
            rule.debit_position.code if rule.debit_position else None
        ) == debit_code
        assert (
            rule.credit_position.code if rule.credit_position else None
        ) == credit_code
