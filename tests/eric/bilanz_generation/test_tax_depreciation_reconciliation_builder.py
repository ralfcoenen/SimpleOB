"""Tests für die ERiC-bestätigte HGBM-AfA-Überleitung."""

from decimal import Decimal

import pytest

from simpleob.eric.bilanz_generation.tax_depreciation_reconciliation_builder import (
    TaxDepreciationReconciliationBuilder,
)
from simpleob.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationKind,
)


def test_builds_confirmed_first_year_reconciliation() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        current_book_value_difference=Decimal("83.33"),
        previous_book_value_difference=Decimal("0.00"),
    )

    assert transfer.kind is TaxReconciliationKind.CHANGE_VALUE

    assert [
        (
            change.concept_name,
            change.actual_period,
            change.previous_period,
        )
        for change in transfer.asset_changes
    ] == [
        (
            "bs.ass.fixAss.tan.otherEquipm.otherbga",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.ass.fixAss.tan.otherEquipm",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.ass.fixAss.tan",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.ass.fixAss",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.ass",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
    ]

    assert [
        (
            change.concept_name,
            change.actual_period,
            change.previous_period,
        )
        for change in transfer.equity_liability_changes
    ] == [
        (
            "bs.eqLiab.equity.netIncome",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.eqLiab.equity.retainedEarnings",
            Decimal("0.00"),
            Decimal("0.00"),
        ),
        (
            "bs.eqLiab.equity",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
        (
            "bs.eqLiab",
            Decimal("83.33"),
            Decimal("0.00"),
        ),
    ]

    assert [
        (
            change.concept_name,
            change.actual_period,
        )
        for change in transfer.income_statement_changes
    ] == [
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss.tan.other"
            ),
            Decimal("-83.33"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss.tan"
            ),
            Decimal("-83.33"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort.fixAss"
            ),
            Decimal("-83.33"),
        ),
        (
            (
                "is.netIncome.regular.operatingTC."
                "deprAmort"
            ),
            Decimal("-83.33"),
        ),
        (
            "is.netIncome.regular.operatingTC",
            Decimal("83.33"),
        ),
        (
            "is.netIncome.eat",
            Decimal("83.33"),
        ),
        (
            "is.netIncome",
            Decimal("83.33"),
        ),
    ]


def test_builds_confirmed_multiyear_reconciliation() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        current_book_value_difference=Decimal("83.33"),
        previous_book_value_difference=Decimal("83.33"),
    )

    equity_changes = {
        change.concept_name: change
        for change in transfer.equity_liability_changes
    }

    assert (
        equity_changes[
            "bs.eqLiab.equity.netIncome"
        ].actual_period
        == Decimal("83.33")
    )
    assert (
        equity_changes[
            "bs.eqLiab.equity.netIncome"
        ].previous_period
        == Decimal("0.00")
    )

    assert (
        equity_changes[
            "bs.eqLiab.equity.retainedEarnings"
        ].actual_period
        == Decimal("0.00")
    )
    assert (
        equity_changes[
            "bs.eqLiab.equity.retainedEarnings"
        ].previous_period
        == Decimal("83.33")
    )

    assert (
        equity_changes[
            "bs.eqLiab.equity"
        ].actual_period
        == Decimal("83.33")
    )
    assert (
        equity_changes[
            "bs.eqLiab.equity"
        ].previous_period
        == Decimal("83.33")
    )

    assert (
        equity_changes["bs.eqLiab"].actual_period
        == Decimal("83.33")
    )
    assert (
        equity_changes["bs.eqLiab"].previous_period
        == Decimal("83.33")
    )

    assert all(
        change.previous_period == Decimal("83.33")
        for change in transfer.asset_changes
    )


def test_quantizes_book_value_differences_to_cents() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        current_book_value_difference=Decimal("83.334"),
        previous_book_value_difference=Decimal("41.664"),
    )

    assert (
        transfer.asset_changes[0].actual_period
        == Decimal("83.33")
    )
    assert (
        transfer.asset_changes[0].previous_period
        == Decimal("41.66")
    )


def test_supports_negative_book_value_difference() -> None:
    transfer = TaxDepreciationReconciliationBuilder.build(
        current_book_value_difference=Decimal("-13.26"),
        previous_book_value_difference=Decimal("0.00"),
    )

    assert (
        transfer.asset_changes[0].actual_period
        == Decimal("-13.26")
    )
    assert (
        transfer.income_statement_changes[0].actual_period
        == Decimal("13.26")
    )
    assert (
        transfer.income_statement_changes[-1].actual_period
        == Decimal("-13.26")
    )


def test_rejects_zero_reconciliation() -> None:
    with pytest.raises(
        ValueError,
        match="at least one book value difference must be non-zero",
    ):
        TaxDepreciationReconciliationBuilder.build(
            current_book_value_difference=Decimal("0.00"),
            previous_book_value_difference=Decimal("0.00"),
        )


@pytest.mark.parametrize(
    (
        "current_difference",
        "previous_difference",
        "message",
    ),
    [
        (
            83.33,
            Decimal("0.00"),
            "current_book_value_difference must be a Decimal",
        ),
        (
            Decimal("83.33"),
            83.33,
            "previous_book_value_difference must be a Decimal",
        ),
    ],
)
def test_rejects_non_decimal_book_value_difference(
    current_difference,
    previous_difference,
    message: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=message,
    ):
        TaxDepreciationReconciliationBuilder.build(
            current_book_value_difference=current_difference,
            previous_book_value_difference=previous_difference,
        )
