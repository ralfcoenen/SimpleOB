"""Tests für steuerliche AfA-Abweichungen."""

from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.tax_depreciation_adjustment import (
    TaxDepreciationAdjustment,
)


def test_tax_depreciation_adjustment_calculates_positive_difference() -> None:
    depreciation_id = uuid4()

    adjustment = TaxDepreciationAdjustment(
        depreciation_id=depreciation_id,
        commercial_amount=Decimal("186.74"),
        tax_amount=Decimal("200.00"),
    )

    assert adjustment.depreciation_id == depreciation_id
    assert adjustment.commercial_amount == Decimal("186.74")
    assert adjustment.tax_amount == Decimal("200.00")
    assert adjustment.difference == Decimal("13.26")


def test_tax_depreciation_adjustment_calculates_negative_difference() -> None:
    adjustment = TaxDepreciationAdjustment(
        depreciation_id=uuid4(),
        commercial_amount=Decimal("200.00"),
        tax_amount=Decimal("186.74"),
    )

    assert adjustment.difference == Decimal("-13.26")


def test_tax_depreciation_adjustment_rejects_equal_amounts() -> None:
    with pytest.raises(
        ValueError,
        match="tax_amount must differ from commercial_amount",
    ):
        TaxDepreciationAdjustment(
            depreciation_id=uuid4(),
            commercial_amount=Decimal("186.74"),
            tax_amount=Decimal("186.74"),
        )


def test_tax_depreciation_adjustment_rejects_non_positive_commercial_amount() -> None:
    with pytest.raises(
        ValueError,
        match="commercial_amount must be greater than 0.00",
    ):
        TaxDepreciationAdjustment(
            depreciation_id=uuid4(),
            commercial_amount=Decimal("0.00"),
            tax_amount=Decimal("100.00"),
        )


def test_tax_depreciation_adjustment_rejects_negative_tax_amount() -> None:
    with pytest.raises(
        ValueError,
        match="tax_amount must not be negative",
    ):
        TaxDepreciationAdjustment(
            depreciation_id=uuid4(),
            commercial_amount=Decimal("100.00"),
            tax_amount=Decimal("-1.00"),
        )


def test_tax_depreciation_adjustment_rejects_invalid_depreciation_id() -> None:
    with pytest.raises(
        TypeError,
        match="depreciation_id must be a UUID",
    ):
        TaxDepreciationAdjustment(
            depreciation_id="invalid",  # type: ignore[arg-type]
            commercial_amount=Decimal("100.00"),
            tax_amount=Decimal("110.00"),
        )
