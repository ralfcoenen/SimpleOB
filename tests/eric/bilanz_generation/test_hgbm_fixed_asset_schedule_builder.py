"""Tests für die HGBM-Ergänzung des Anlagenspiegels."""

from decimal import Decimal

import pytest

from openbilanz.eric.bilanz_generation.hgbm_fixed_asset_schedule_builder import (
    HgbmFixedAssetScheduleBuilder,
)


@pytest.mark.parametrize(
    ("concept_name", "expected"),
    [
        (
            "accDepr.DeprPeriod.regular",
            Decimal("13.26"),
        ),
        (
            "accDepr.DeprPeriod",
            Decimal("13.26"),
        ),
        (
            "accDepr",
            Decimal("13.26"),
        ),
        (
            "all",
            Decimal("-13.26"),
        ),
        (
            "grossCost.beginning",
            Decimal("0.00"),
        ),
        (
            "gross.addition",
            Decimal("0.00"),
        ),
        (
            "gross.release",
            Decimal("0.00"),
        ),
        (
            "gross",
            Decimal("0.00"),
        ),
        (
            "accDepr.beginning",
            Decimal("0.00"),
        ),
        (
            "accDepr.release",
            Decimal("0.00"),
        ),
    ],
)
def test_difference_for_confirmed_v10_bal_fact(
    concept_name: str,
    expected: Decimal,
) -> None:
    result = HgbmFixedAssetScheduleBuilder._difference_for_concept(
        concept_name=concept_name,
        additional_tax_depreciation=Decimal("13.26"),
    )

    assert result == expected


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
    ],
)
def test_rejects_non_positive_additional_tax_depreciation(
    amount: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        HgbmFixedAssetScheduleBuilder.build(
            commercial_contexts={},
            commercial_facts=(),
            commercial_nil_facts=(),
            additional_tax_depreciation=amount,
        )


def test_rejects_non_decimal_additional_tax_depreciation() -> None:
    with pytest.raises(
        TypeError,
        match="must be a Decimal",
    ):
        HgbmFixedAssetScheduleBuilder.build(
            commercial_contexts={},
            commercial_facts=(),
            commercial_nil_facts=(),
            additional_tax_depreciation=13.26,  # type: ignore[arg-type]
        )
