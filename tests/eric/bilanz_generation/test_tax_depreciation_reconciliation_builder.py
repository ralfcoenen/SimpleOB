"""Tests für die bestätigte HGBM-AfA-Überleitung."""

from decimal import Decimal

import pytest

from openbilanz.eric.bilanz_generation.tax_depreciation_reconciliation_builder import (
    TaxDepreciationReconciliationBuilder,
)
from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationKind,
)


def test_builds_confirmed_hgbm_depreciation_reconciliation() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        additional_tax_depreciation=Decimal("13.26"),
    )

    assert transfer.kind is TaxReconciliationKind.CHANGE_VALUE

    assert [
        (change.concept_name, change.actual_period)
        for change in transfer.asset_changes
    ] == [
        (
            "bs.ass.fixAss.tan.otherEquipm.otherbga",
            Decimal("-13.26"),
        ),
        (
            "bs.ass.fixAss.tan.otherEquipm",
            Decimal("-13.26"),
        ),
        (
            "bs.ass.fixAss.tan",
            Decimal("-13.26"),
        ),
        (
            "bs.ass.fixAss",
            Decimal("-13.26"),
        ),
        (
            "bs.ass",
            Decimal("-13.26"),
        ),
    ]

    assert [
        (change.concept_name, change.actual_period)
        for change in transfer.equity_liability_changes
    ] == [
        (
            "bs.eqLiab.equity.netIncome",
            Decimal("-13.26"),
        ),
        (
            "bs.eqLiab.equity",
            Decimal("-13.26"),
        ),
        (
            "bs.eqLiab",
            Decimal("-13.26"),
        ),
    ]

    assert [
        (change.concept_name, change.actual_period)
        for change in transfer.income_statement_changes
    ] == [
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss.tan.other"
            ),
            Decimal("13.26"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss.tan"
            ),
            Decimal("13.26"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss"
            ),
            Decimal("13.26"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort"
            ),
            Decimal("13.26"),
        ),
        (
            "is.netIncome.regular.operatingTC",
            Decimal("-13.26"),
        ),
        (
            "is.netIncome.eat",
            Decimal("-13.26"),
        ),
        (
            "is.netIncome",
            Decimal("-13.26"),
        ),
    ]


def test_quantizes_depreciation_difference_to_cents() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        additional_tax_depreciation=Decimal("13.264"),
    )

    assert transfer.asset_changes[0].actual_period == Decimal("-13.26")
    assert (
        transfer.income_statement_changes[0].actual_period
        == Decimal("13.26")
    )


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0"),
        Decimal("-0.01"),
    ],
)
def test_rejects_non_positive_depreciation_difference(
    amount: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        TaxDepreciationReconciliationBuilder.build(
            additional_tax_depreciation=amount,
        )


def test_rejects_non_decimal_depreciation_difference() -> None:
    with pytest.raises(
        TypeError,
        match="must be a Decimal",
    ):
        TaxDepreciationReconciliationBuilder.build(
            additional_tax_depreciation=13.26,  # type: ignore[arg-type]
        )
