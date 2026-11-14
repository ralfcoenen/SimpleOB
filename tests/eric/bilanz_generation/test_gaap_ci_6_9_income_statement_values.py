"""Tests für GAAP-CI-GuV-Werte der Taxonomie 6.9."""

from decimal import Decimal

from simpleob.domain.fixed_asset_disposal_detail import (
    FixedAssetDisposalDetail,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_income_statement_values import (
    GaapCi69IncomeStatementValueBuilder,
)
from simpleob.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)


def _fixed_asset_schedule(
    amount: Decimal,
) -> tuple[FixedAssetSchedulePosition, ...]:
    return (
        FixedAssetSchedulePosition(
            position_code="HGB.266.AKTIVA.A.II.3",
            acquisition_cost_beginning=Decimal("5000.00"),
            additions=Decimal("0.00"),
            disposals=Decimal("0.00"),
            acquisition_cost_ending=Decimal("5000.00"),
            accumulated_depreciation_beginning=Decimal("0.00"),
            depreciation_current_year=amount,
            depreciation_disposals=Decimal("0.00"),
            accumulated_depreciation_ending=amount,
            carrying_amount_ending=(Decimal("5000.00") - amount),
        ),
    )


def test_mapped_depreciation_replaces_generic_other_leaf() -> None:
    values = {}

    GaapCi69IncomeStatementValueBuilder._add_fixed_asset_depreciation_values(
        values=values,
        fixed_asset_schedule=_fixed_asset_schedule(
            Decimal("833.33")
        ),
        mapped_tangible_depreciation=Decimal("833.33"),
    )

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort.fixAss.tan",
        )
    ] == Decimal("833.33")
    assert (
        "is.netIncome.regular.operatingTC."
        "deprAmort.fixAss.tan.other",
    ) not in values


def test_unmapped_depreciation_remains_in_generic_other_leaf() -> None:
    values = {}

    GaapCi69IncomeStatementValueBuilder._add_fixed_asset_depreciation_values(
        values=values,
        fixed_asset_schedule=_fixed_asset_schedule(
            Decimal("833.33")
        ),
        mapped_tangible_depreciation=Decimal("500.00"),
    )

    assert values[
        (
            "is.netIncome.regular.operatingTC."
            "deprAmort.fixAss.tan.other",
        )
    ] == Decimal("333.33")


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
