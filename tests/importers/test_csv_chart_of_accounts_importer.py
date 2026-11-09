import json
from dataclasses import replace
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
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundleImporter,
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


def _position_provider_for_template_import():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    return HgbFinancialStatementPositionProvider(
        (assets, liabilities, income_statement)
    )


def test_loads_standard_chart_with_reusable_configuration():
    resources = Path("src/simpleob/resources")
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter(
            position_provider=_position_provider_for_template_import()
        )
    )

    bundle = importer.load(
        resources / "chart_of_accounts/openbilanz_standard.csv"
    )

    assert bundle.chart.name == "openbilanz_standard"
    assert bundle.control_accounts is not None
    assert bundle.control_accounts.opening_balance_account == "9000"
    assert bundle.vat_accounts is not None
    assert bundle.vat_accounts.input_tax_7 == "1571"
    assert bundle.account_roles is not None
    assert bundle.account_roles.customer_receivables == frozenset({"1400"})
    assert bundle.taxonomy_version == "6.9"
    assert bundle.taxonomy_mappings


def test_rejects_incompatible_system_account_type():
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter(
            position_provider=_position_provider_for_template_import()
        )
    )
    bundle = importer.load(
        Path("src/simpleob/resources/chart_of_accounts/openbilanz_standard.csv")
    )
    assert bundle.control_accounts is not None
    invalid = replace(
        bundle,
        control_accounts=replace(
            bundle.control_accounts,
            opening_balance_account="1000",
        ),
    )

    with pytest.raises(
        ValueError,
        match="Technisches Konto Eröffnungsbilanz 1000 erwartet Kontotyp EQUITY",
    ):
        importer.validate(invalid)


def test_custom_csv_without_sidecar_needs_configuration_later(tmp_path: Path):
    csv_file = tmp_path / "custom.csv"
    csv_file.write_text(
        "account_number;name;account_type\n"
        "7000;Bankkonto;ASSET\n"
        "7001;Umsatzsteuer;LIABILITY\n",
        encoding="utf-8",
    )
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter()
    )

    bundle = importer.load(csv_file)

    assert bundle.chart.accounts[0].account_number == "7000"
    assert bundle.control_accounts is None
    assert bundle.vat_accounts is None
    assert bundle.account_roles is None
    assert bundle.taxonomy_mappings is None


def test_imports_alternative_prepared_chart_and_companion_configuration(
    tmp_path: Path,
):
    csv_file = tmp_path / "skr_custom.csv"
    csv_file.write_text(
        "account_number;name;account_type\n"
        "7000;Eigenkapital;EQUITY\n"
        "7001;Verbindlichkeit;LIABILITY\n"
        "7002;Aufwand;EXPENSE\n"
        "7003;Ertrag;REVENUE\n"
        "7004;Aktivkonto;ASSET\n",
        encoding="utf-8",
    )
    controls = {
        "opening_balance_account": "7000",
        "income_summary_account": "7000",
        "profit_account": "7000",
        "loss_account": "7000",
        "profit_loss_carryforward_account": "7000",
        "statutory_reserve_account": "7000",
        "other_revenue_reserves_account": "7000",
        "distribution_liability_account": "7001",
        "depreciation_expense_account": "7002",
        "fixed_asset_disposal_gain_account": "7003",
        "fixed_asset_disposal_loss_account": "7002",
    }
    config = {
        "format_version": 1,
        "system_accounts": controls,
        "vat_accounts": {
            "input_tax_7": "7004",
            "input_tax_19": "7004",
            "output_tax_7": "7001",
            "output_tax_19": "7001",
        },
        "account_roles": {"cash_accounts": ["7004"]},
    }
    csv_file.with_name("skr_custom.config.json").write_text(
        json.dumps(config),
        encoding="utf-8",
    )
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter()
    )

    bundle = importer.load(csv_file)

    assert bundle.control_accounts is not None
    assert bundle.control_accounts.opening_balance_account == "7000"
    assert bundle.vat_accounts is not None
    assert bundle.vat_accounts.output_tax_19 == "7001"
    assert bundle.account_roles is not None
    assert bundle.account_roles.cash_accounts == frozenset({"7004"})

    reusable_csv = tmp_path / "reusable.csv"
    reusable_csv.write_text(csv_file.read_text(encoding="utf-8"), encoding="utf-8")
    reusable_bundle = importer.load(reusable_csv)
    reusable_bundle = replace(
        reusable_bundle,
        control_accounts=bundle.control_accounts,
        vat_accounts=bundle.vat_accounts,
        account_roles=bundle.account_roles,
    )
    config_path = reusable_csv.with_name("reusable.config.json")
    importer.save_configuration(reusable_bundle, config_path)
    reloaded = importer.load(reusable_csv)
    assert reloaded.control_accounts == bundle.control_accounts
    assert reloaded.vat_accounts == bundle.vat_accounts
    assert reloaded.account_roles == bundle.account_roles


def test_rejects_unsupported_taxonomy_version(tmp_path: Path):
    csv_file = tmp_path / "custom.csv"
    csv_file.write_text(
        "account_number;name;account_type\n"
        "7000;Eigenkapital;EQUITY\n"
        "7001;Verbindlichkeit;LIABILITY\n"
        "7002;Aufwand;EXPENSE\n"
        "7003;Ertrag;REVENUE\n"
        "7004;Aktivkonto;ASSET\n",
        encoding="utf-8",
    )
    controls = {
        "opening_balance_account": "7000",
        "income_summary_account": "7000",
        "profit_account": "7000",
        "loss_account": "7000",
        "profit_loss_carryforward_account": "7000",
        "statutory_reserve_account": "7000",
        "other_revenue_reserves_account": "7000",
        "distribution_liability_account": "7001",
        "depreciation_expense_account": "7002",
        "fixed_asset_disposal_gain_account": "7003",
        "fixed_asset_disposal_loss_account": "7002",
    }
    config = {
        "format_version": 1,
        "system_accounts": controls,
        "vat_accounts": {
            "input_tax_7": "7004",
            "input_tax_19": "7004",
            "output_tax_7": "7001",
            "output_tax_19": "7001",
        },
        "taxonomy_version": "6.8",
    }
    csv_file.with_name("custom.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter()
    )

    with pytest.raises(ValueError, match="ausschließlich Version 6.9"):
        importer.load(csv_file)


def test_rejects_template_configuration_with_unknown_account(tmp_path: Path):
    csv_file = tmp_path / "custom.csv"
    csv_file.write_text(
        "account_number;name;account_type\n"
        "7000;Bankkonto;ASSET\n"
        "7001;Umsatzsteuer;LIABILITY\n",
        encoding="utf-8",
    )
    controls = {
        field: "7000"
        for field in (
            "opening_balance_account",
            "income_summary_account",
            "profit_account",
            "loss_account",
            "profit_loss_carryforward_account",
            "statutory_reserve_account",
            "other_revenue_reserves_account",
            "distribution_liability_account",
            "depreciation_expense_account",
            "fixed_asset_disposal_gain_account",
            "fixed_asset_disposal_loss_account",
        )
    }
    controls["profit_account"] = "9999"
    config = {
        "format_version": 1,
        "system_accounts": controls,
        "vat_accounts": {
            "input_tax_7": "7000",
            "input_tax_19": "7000",
            "output_tax_7": "7001",
            "output_tax_19": "7001",
        },
    }
    csv_file.with_name("custom.config.json").write_text(
        json.dumps(config),
        encoding="utf-8",
    )
    importer = ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter()
    )

    with pytest.raises(ValueError, match="nicht vorhandene Konten"):
        importer.load(csv_file)




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

