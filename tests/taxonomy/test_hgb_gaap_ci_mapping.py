"""Tests für das HGB-zu-GAAP-CI-Mapping."""


import pytest

from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from tests.taxonomy_resources import taxonomy_entry_point


def test_hgb_gaap_ci_mapping_contains_expected_rules() -> None:
    """Das produktive Mapping enthält die erwarteten HGB-Zuordnungen."""

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement = (
        create_hgb_income_statement_structure()
    )

    mapping_set = create_hgb_gaap_ci_mapping(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )

    assert len(mapping_set.rules) == 88

    rules_by_code = {
        rule.position.code: rule
        for rule in mapping_set.rules
    }

    assert rules_by_code[
        "HGB.266.AKTIVA.A"
    ].concept_name == "bs.ass.fixAss"

    assert rules_by_code[
        "HGB.266.AKTIVA.B.III.2"
    ].concept_name == (
        "bs.ass.currAss.securities.other"
    )

    assert rules_by_code[
        "HGB.266.PASSIVA.A.V"
    ].concept_name == (
        "bs.eqLiab.equity.netIncome"
    )

    assert rules_by_code[
        "HGB.275.GKV.1"
    ].concept_name == (
        "is.netIncome.regular."
        "operatingTC.grossTradingProfit."
        "totalOutput.netSales"
    )

    assert rules_by_code[
        "HGB.275.GKV.17"
    ].concept_name == "is.netIncome"

    assert "HGB.275.GKV" not in rules_by_code

def test_hgb_gaap_ci_mapping_is_valid_for_taxonomy_6_8() -> None:
    """Alle produktiven Mapping-Ziele existieren in Taxonomie 6.8."""

    entry_point = taxonomy_entry_point("6.8")


    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement = (
        create_hgb_income_statement_structure()
    )

    mapping_set = create_hgb_gaap_ci_mapping(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point
        )

        result = mapping_set.validate(
            taxonomy_model
        )

    finally:
        adapter.close()

    assert result.is_valid
    assert result.valid_count == 88
    assert result.missing_count == 0
    assert result.missing_concept_names == ()
    
@pytest.mark.parametrize("version", ("6.8", "6.9", "6.10"))
def test_hgb_gaap_ci_mapping_is_valid_for_supported_taxonomies(
    version: str,
) -> None:
    """Alle produktiven Mapping-Ziele existieren in unterstützten Taxonomien."""
    entry_point = taxonomy_entry_point(version)


    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement = (
        create_hgb_income_statement_structure()
    )

    mapping_set = create_hgb_gaap_ci_mapping(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point
        )

        result = mapping_set.validate(
            taxonomy_model
        )

    finally:
        adapter.close()

    assert result.is_valid, (
        f"Missing concepts: "
        f"{result.missing_concept_names}"
    )

    assert result.valid_count == 88
    assert result.missing_count == 0


