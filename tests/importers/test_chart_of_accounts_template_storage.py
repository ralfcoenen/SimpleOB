from dataclasses import replace
from pathlib import Path

import pytest

from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundleImporter,
)
from simpleob.importers.csv_account_taxonomy_mapping_importer import (
    CsvAccountTaxonomyMappingImporter,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)


def _importer() -> ChartOfAccountsTemplateBundleImporter:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    return ChartOfAccountsTemplateBundleImporter(
        chart_importer=CsvChartOfAccountsImporter(
            position_provider=HgbFinancialStatementPositionProvider(
                (assets, liabilities, income_statement)
            )
        )
    )


def _standard_source() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "src/simpleob/resources/chart_of_accounts/openbilanz_standard.csv"
    )


def test_save_and_reload_preserves_bundle_without_changing_source(tmp_path):
    importer = _importer()
    source_path = _standard_source()
    source_csv = source_path.read_bytes()
    source_config = source_path.with_name(
        "openbilanz_standard.config.json"
    ).read_bytes()
    source_mapping = (
        source_path.parents[1]
        / "e_bilanz/account_mappings/6.9/openbilanz_standard.csv"
    )
    source_taxonomy = source_mapping.read_bytes()
    bundle = importer.load(source_path)

    saved_csv = importer.save_template(
        bundle,
        tmp_path / "user-templates",
        "Mein Kontenrahmen",
    )
    reloaded = importer.load(saved_csv)

    assert reloaded.chart.name == "Mein_Kontenrahmen"
    assert reloaded.chart.accounts == bundle.chart.accounts
    assert reloaded.chart.account_mapping_rules == bundle.chart.account_mapping_rules
    assert reloaded.control_accounts == bundle.control_accounts
    assert reloaded.vat_accounts == bundle.vat_accounts
    assert reloaded.account_roles == bundle.account_roles
    assert reloaded.taxonomy_version == bundle.taxonomy_version
    assert reloaded.taxonomy_mappings == bundle.taxonomy_mappings
    assert not any(
        rule.account_number == "8990"
        for rule in reloaded.chart.account_mapping_rules
    )
    assert not any(
        rule.account_number == "9000"
        for rule in reloaded.chart.account_mapping_rules
    )
    assert saved_csv.with_name("Mein_Kontenrahmen.taxonomy.csv").is_file()
    assert source_path.read_bytes() == source_csv
    assert source_path.with_name("openbilanz_standard.config.json").read_bytes() == source_config
    assert source_mapping.read_bytes() == source_taxonomy


def test_save_without_taxonomy_mappings_does_not_create_mapping_file(tmp_path):
    importer = _importer()
    bundle = importer.load(_standard_source())
    bundle = replace(
        bundle,
        taxonomy_version=None,
        taxonomy_mappings=None,
    )

    saved_csv = importer.save_template(
        bundle,
        tmp_path / "templates",
        "Ohne Taxonomie",
    )
    config_path = saved_csv.with_name("Ohne_Taxonomie.config.json")
    reloaded = importer.load(saved_csv)

    assert not saved_csv.with_name("Ohne_Taxonomie.taxonomy.csv").exists()
    assert "taxonomy_mapping_file" not in config_path.read_text(encoding="utf-8")
    assert reloaded.taxonomy_mappings == {}
    assert reloaded.taxonomy_version == "6.9"


def test_taxonomy_mapping_import_rejects_missing_field_value(tmp_path):
    taxonomy_csv = tmp_path / "incomplete.taxonomy.csv"
    taxonomy_csv.write_text(
        "account_number;concept_name\n7000;\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Taxonomieposition darf nicht leer sein"):
        CsvAccountTaxonomyMappingImporter().load(taxonomy_csv)


def test_existing_template_is_not_overwritten(tmp_path):
    importer = _importer()
    bundle = importer.load(_standard_source())
    template_root = tmp_path / "templates"
    saved_csv = importer.save_template(bundle, template_root, "Sicher")
    original_files = {
        path.relative_to(saved_csv.parent): path.read_bytes()
        for path in saved_csv.parent.iterdir()
    }

    with pytest.raises(FileExistsError):
        importer.save_template(bundle, template_root, "Sicher")

    assert {
        path.relative_to(saved_csv.parent): path.read_bytes()
        for path in saved_csv.parent.iterdir()
    } == original_files


def test_failed_write_leaves_no_partial_template(tmp_path, monkeypatch):
    importer = _importer()
    bundle = importer.load(_standard_source())
    template_root = tmp_path / "templates"

    def fail_after_partial_taxonomy_csv(_mappings, path):
        path.write_text("partial", encoding="utf-8")
        raise OSError("simulierter Schreibfehler")

    monkeypatch.setattr(
        importer._taxonomy_importer,
        "save",
        fail_after_partial_taxonomy_csv,
    )

    with pytest.raises(OSError, match="simulierter Schreibfehler"):
        importer.save_template(bundle, template_root, "Fehlerfall")

    assert list(template_root.iterdir()) == []
