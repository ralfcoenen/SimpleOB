from pathlib import Path

import pytest

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
from simpleob.importers.errors import (
    ChartOfAccountsImportError,
)


def test_imports_single_account(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type\n"
            "8400;Umsatzerlöse;REVENUE\n"
        ),
        encoding="utf-8",
    )

    template = CsvChartOfAccountsImporter().load(csv_file)

    assert template.name == "accounts"
    assert len(template.accounts) == 1

    account = template.accounts[0]

    assert account.account_number == "8400"
    assert account.name == "Umsatzerlöse"
    assert account.account_type is AccountType.REVENUE


def test_imports_multiple_accounts(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type\n"
            "1200;Bank;ASSET\n"
            "8400;Umsatzerlöse;REVENUE\n"
            "4400;Wareneingang;EXPENSE\n"
        ),
        encoding="utf-8",
    )

    template = CsvChartOfAccountsImporter().load(csv_file)

    assert template.name == "accounts"
    assert len(template.accounts) == 3

    assert template.accounts[0].account_number == "1200"
    assert template.accounts[0].name == "Bank"
    assert template.accounts[0].account_type is AccountType.ASSET

    assert template.accounts[1].account_number == "8400"
    assert template.accounts[1].name == "Umsatzerlöse"
    assert template.accounts[1].account_type is AccountType.REVENUE

    assert template.accounts[2].account_number == "4400"
    assert template.accounts[2].name == "Wareneingang"
    assert template.accounts[2].account_type is AccountType.EXPENSE


def test_rejects_unknown_account_type(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type\n"
            "8400;Umsatzerlöse;SALES\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ChartOfAccountsImportError,
        match="Unbekannter Kontotyp",
    ):
        CsvChartOfAccountsImporter().load(csv_file)

def test_rejects_missing_account_type_column(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name\n"
            "1200;Bank\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ChartOfAccountsImportError,
        match="Fehlende Spalte",
    ):
        CsvChartOfAccountsImporter().load(csv_file)




def test_imports_account_mapping_rule_for_revenue_account(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "8400;Umsatzerlöse;REVENUE;INCOME_STATEMENT;;"
            "HGB.275.GKV.1\n"
        ),
        encoding="utf-8",
    )

    provider = HgbFinancialStatementPositionProvider(
        create_hgb_income_statement_structure(),
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    assert len(template.accounts) == 1
    assert len(template.account_mapping_rules) == 1

    rule = template.account_mapping_rules[0]

    assert rule.account_number == "8400"
    assert rule.debit_position is None
    assert rule.credit_position is not None
    assert rule.credit_position.code == "HGB.275.GKV.1"

def test_imports_account_mapping_rule_for_expense_account(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "4930;Sonstige betriebliche Aufwendungen;"
            "EXPENSE;INCOME_STATEMENT;"
            "HGB.275.GKV.8;\n"
        ),
        encoding="utf-8",
    )

    provider = HgbFinancialStatementPositionProvider(
        create_hgb_income_statement_structure(),
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    assert len(template.account_mapping_rules) == 1

    rule = template.account_mapping_rules[0]

    assert rule.account_number == "4930"
    assert rule.debit_position is not None
    assert rule.debit_position.code == "HGB.275.GKV.8"
    assert rule.credit_position is None

def test_imports_account_mapping_rule_for_asset_account(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "1200;Bank;ASSET;BALANCE_SHEET;"
            "HGB.266.AKTIVA.B.IV;\n"
        ),
        encoding="utf-8",
    )

    assets, _ = create_hgb_balance_sheet_structure()

    provider = HgbFinancialStatementPositionProvider(
        assets,
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    assert len(template.accounts) == 1
    assert len(template.account_mapping_rules) == 1

    account = template.accounts[0]
    rule = template.account_mapping_rules[0]

    assert account.account_number == "1200"
    assert account.account_type is AccountType.ASSET

    assert rule.account_number == "1200"
    assert rule.debit_position is not None
    assert rule.debit_position.code == "HGB.266.AKTIVA.B.IV"
    assert rule.credit_position is None

def test_imports_account_mapping_rule_for_liability_account(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "1600;Verbindlichkeiten;LIABILITY;BALANCE_SHEET;;"
            "HGB.266.PASSIVA.C\n"
        ),
        encoding="utf-8",
    )

    _, liabilities = create_hgb_balance_sheet_structure()

    provider = HgbFinancialStatementPositionProvider(
        liabilities,
    )

    template = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    assert len(template.accounts) == 1
    assert len(template.account_mapping_rules) == 1

    account = template.accounts[0]
    rule = template.account_mapping_rules[0]

    assert account.account_number == "1600"
    assert account.account_type is AccountType.LIABILITY

    assert rule.account_number == "1600"
    assert rule.debit_position is None
    assert rule.credit_position is not None
    assert rule.credit_position.code == "HGB.266.PASSIVA.C"
    
def test_rejects_balance_sheet_statement_type_for_income_statement_position(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "8400;Umsatzerlöse;REVENUE;BALANCE_SHEET;;"
            "HGB.275.GKV.1\n"
        ),
        encoding="utf-8",
    )

    provider = HgbFinancialStatementPositionProvider(
        create_hgb_income_statement_structure(),
    )

    with pytest.raises(
        ChartOfAccountsImportError,
        match="statement_type",
    ):
        CsvChartOfAccountsImporter(
            position_provider=provider,
        ).load(csv_file)

def test_rejects_unknown_statement_type(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "accounts.csv"

    csv_file.write_text(
        (
            "account_number;name;account_type;statement_type;"
            "debit_position_code;credit_position_code\n"
            "8400;Umsatzerlöse;REVENUE;STATEMENT;;"
            "HGB.275.GKV.1\n"
        ),
        encoding="utf-8",
    )

    provider = HgbFinancialStatementPositionProvider(
        create_hgb_income_statement_structure(),
    )

    with pytest.raises(
        ChartOfAccountsImportError,
        match="Unbekannter statement_type",
    ):
        CsvChartOfAccountsImporter(
            position_provider=provider,
        ).load(csv_file)

