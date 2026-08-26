"""Tests für die Buchwertermittlung von Anlagegütern."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.services.fixed_asset_book_value_service import (
    FixedAssetBookValueService,
)


def _asset() -> FixedAsset:
    return FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=120,
    )


def _depreciation(
    *,
    fixed_asset_id,
    depreciation_date: date,
    amount: Decimal,
) -> FixedAssetDepreciation:
    return FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(
            depreciation_date.year,
            12,
            31,
        ),
        depreciation_date=depreciation_date,
        amount=amount,
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )


def test_returns_acquisition_cost_without_depreciation() -> None:
    asset = _asset()

    repository = Mock()
    repository.list_for_fixed_asset.return_value = ()

    service = FixedAssetBookValueService(
        depreciation_repository=repository,
    )

    result = service.book_value_at(
        fixed_asset=asset,
        reference_date=date(2026, 8, 15),
    )

    assert result == Decimal("12000.00")


def test_subtracts_booked_depreciation_until_reference_date() -> None:
    asset = _asset()

    repository = Mock()
    repository.list_for_fixed_asset.return_value = (
        _depreciation(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2025, 12, 31),
            amount=Decimal("1200.00"),
        ),
        _depreciation(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2026, 8, 15),
            amount=Decimal("800.00"),
        ),
    )

    service = FixedAssetBookValueService(
        depreciation_repository=repository,
    )

    result = service.book_value_at(
        fixed_asset=asset,
        reference_date=date(2026, 8, 15),
    )

    assert result == Decimal("10000.00")


def test_ignores_depreciation_after_reference_date() -> None:
    asset = _asset()

    repository = Mock()
    repository.list_for_fixed_asset.return_value = (
        _depreciation(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2025, 12, 31),
            amount=Decimal("1200.00"),
        ),
        _depreciation(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2026, 12, 31),
            amount=Decimal("1200.00"),
        ),
    )

    service = FixedAssetBookValueService(
        depreciation_repository=repository,
    )

    result = service.book_value_at(
        fixed_asset=asset,
        reference_date=date(2026, 8, 15),
    )

    assert result == Decimal("10800.00")


def test_rejects_depreciation_above_acquisition_cost() -> None:
    asset = _asset()

    repository = Mock()
    repository.list_for_fixed_asset.return_value = (
        _depreciation(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2026, 8, 15),
            amount=Decimal("12001.00"),
        ),
    )

    service = FixedAssetBookValueService(
        depreciation_repository=repository,
    )

    with pytest.raises(
        ValueError,
        match="übersteigen",
    ):
        service.book_value_at(
            fixed_asset=asset,
            reference_date=date(2026, 8, 15),
        )
