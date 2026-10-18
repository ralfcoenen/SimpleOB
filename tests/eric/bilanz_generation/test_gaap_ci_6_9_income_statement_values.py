"""Tests für GAAP-CI-GuV-Werte der Taxonomie 6.9."""

from decimal import Decimal

from simpleob.domain.fixed_asset_disposal_detail import (
    FixedAssetDisposalDetail,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_income_statement_values import (
    GaapCi69IncomeStatementValueBuilder,
)

def test_adds_fixed_asset_disposal_details() -> None:
    """Gewinn und Verlust aus Anlagenabgängen bleiben getrennt."""

    values = {}

    loss_detail = FixedAssetDisposalDetail(
        position_code="HGB.266.AKTIVA.A.II.3",
        carrying_amount=Decimal("1625.00"),
        net_proceeds=Decimal("840.34"),
    )

    gain_detail = FixedAssetDisposalDetail(
        position_code="HGB.266.AKTIVA.A.I.1",
        carrying_amount=Decimal("1000.00"),
        net_proceeds=Decimal("1500.00"),
    )

    GaapCi69IncomeStatementValueBuilder._add_fixed_asset_disposal_values(
        values=values,
        fixed_asset_disposal_details=(
            loss_detail,
            gain_detail,
        ),
    )

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss",
        )
    ] == Decimal("784.66")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss.sale",
        )
    ] == Decimal("840.34")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss.bookValue",
        )
    ] == Decimal("1625.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherOpRevenue.disposFixAss",
        )
    ] == Decimal("500.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherOpRevenue.disposFixAss.sale",
        )
    ] == Decimal("1500.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherOpRevenue.disposFixAss.bookValue",
        )
    ] == Decimal("1000.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss.sale.tan",
        )
    ] == Decimal("840.34")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss.bookValue.tan",
        )
    ] == Decimal("1625.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherOpRevenue.disposFixAss.sale.intan",
        )
    ] == Decimal("1500.00")

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "otherOpRevenue.disposFixAss.bookValue.intan",
        )
    ] == Decimal("1000.00")
