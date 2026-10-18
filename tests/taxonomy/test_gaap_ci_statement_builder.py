"""Tests für die GAAP-CI-Aufbereitung eines HGB-Abschlusses."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.gaap_ci_statement_builder import (
    GaapCiStatementBuilder,
)

TEST_ENTITY_SCHEME = "http://www.bundesfinanzministerium.de"


def _positions_by_code(*roots):
    result = {}

    def walk(position):
        result[position.code] = position
        for child in position.children:
            walk(child)

    for root in roots:
        walk(root)

    return result


@pytest.mark.integration
def test_builds_gaap_ci_statement_from_hgb_amounts() -> None:
    """HGB-Bilanz und GuV werden gemeinsam zu GAAP-CI-Facts."""

    entry_point = Path(
    "/tmp/openbilanz-taxonomy/6.9/"
    "de-gaap-ci-2025-04-01/"
    "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    if not entry_point.is_file():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    positions = _positions_by_code(
        assets,
        liabilities,
        income_statement,
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point
        )

        builder = GaapCiStatementBuilder(
            taxonomy_model=taxonomy_model,
            assets=assets,
            liabilities=liabilities,
            income_statement=income_statement,
        )

        statement = builder.build(
            amounts={
                positions["HGB.266.AKTIVA.B.IV"]:
                    Decimal("10000.00"),
                positions["HGB.266.PASSIVA.A.I"]:
                    Decimal("10000.00"),
                positions["HGB.275.GKV.1"]:
                    Decimal("5000.00"),
                positions["HGB.275.GKV.8"]:
                    Decimal("2000.00"),
            },
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            fiscal_year_start=date(2025, 1, 1),
            fiscal_year_end=date(2025, 12, 31),
        )

        facts_by_name = {
            fact.concept.name: fact
            for fact in statement.facts
        }

        assert (
            facts_by_name["bs.ass.currAss.cashEquiv"].amount
            == Decimal("10000.00")
        )
        assert (
            facts_by_name["bs.eqLiab.equity.subscribed"].amount
            == Decimal("10000.00")
        )
        assert (
            facts_by_name[
                "is.netIncome.regular.operatingTC."
                "grossTradingProfit.totalOutput.netSales"
            ].amount
            == Decimal("5000.00")
        )
        assert (
            facts_by_name[
                "is.netIncome.regular.operatingTC.otherCost"
            ].amount
            == Decimal("2000.00")
        )

        assert all(
            fact.context.start_date is None
            for fact in statement.balance_sheet_facts
        )

        assert all(
            fact.context.start_date == date(2025, 1, 1)
            for fact in statement.income_statement_facts
        )

    finally:
        adapter.close()


def test_ignores_unmapped_hgb_structure_positions() -> None:
    """Reine HGB-Strukturpositionen benötigen kein Taxonomie-Mapping."""

    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    assert income_statement.code == "HGB.275.GKV"

