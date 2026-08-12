"""Tests für das HGB-zu-GAAP-CI-Mapping."""

from pathlib import Path

import pytest

from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)


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

    assert len(mapping_set.rules) == 86

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

    entry_point = Path(
        "/tmp/openbilanz-taxonomy/6.8/"
        "german-gaap-taxonomy-v6.8-2024-04-01/"
        "xbrl/de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )

    if not entry_point.is_file():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

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
    assert result.valid_count == 86
    assert result.missing_count == 0
    assert result.missing_concept_names == ()
    
@pytest.mark.parametrize(
    "entry_point",
    (
        Path(
            "/tmp/openbilanz-taxonomy/6.8/"
            "german-gaap-taxonomy-v6.8-2024-04-01/"
            "xbrl/de-gaap-ci-2024-04-01/"
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        Path(
            "/tmp/openbilanz-taxonomy/6.9/"
            "de-gaap-ci-2025-04-01/"
            "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
        ),
        Path(
            "/tmp/openbilanz-taxonomy/6.10/"
            "de-gaap-ci-2026-04-01/"
            "de-gaap-ci-2026-04-01-shell-fiscal.xsd"
        ),
    ),
)
def test_hgb_gaap_ci_mapping_is_valid_for_supported_taxonomies(
    entry_point: Path,
) -> None:
    """Alle produktiven Mapping-Ziele existieren in unterstützten Taxonomien."""

    if not entry_point.is_file():
        pytest.skip(
            f"Taxonomy is not installed locally: {entry_point}"
        )

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

    assert result.valid_count == 86
    assert result.missing_count == 0


