from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)


def _fixed_asset(**changes) -> FixedAsset:
    values = {
    "company_id": uuid4(),
    "asset_code": "A-0001",
    "description": "MacBook Pro",
    "position_code": "HGB.266.AKTIVA.A.II.3",
    "asset_account_number": "0690",
    "depreciation_expense_account_number": "4830",
    "acquisition_date": date(2026, 3, 15),
    "acquisition_cost": Decimal("2400.00"),
    "depreciation_start_date": date(2026, 3, 15),
    "useful_life_months": 36,
}

    values.update(changes)

    return FixedAsset(**values)


def test_creates_active_fixed_asset() -> None:
    asset = _fixed_asset()

    assert asset.asset_code == "A-0001"
    assert asset.acquisition_cost == Decimal("2400.00")
    assert asset.status is FixedAssetStatus.ACTIVE
    assert asset.disposal_date is None


def test_normalizes_text_fields() -> None:
    asset = _fixed_asset(
        asset_code=" A-0001 ",
        description=" MacBook Pro ",
        position_code=" HGB.266.AKTIVA.A.II.3 ",
    )

    assert asset.asset_code == "A-0001"
    assert asset.description == "MacBook Pro"
    assert (
        asset.position_code
        == "HGB.266.AKTIVA.A.II.3"
    )


def test_rejects_non_fixed_asset_position() -> None:
    with pytest.raises(ValueError):
        _fixed_asset(
            position_code="HGB.266.AKTIVA.B.IV"
        )


def test_rejects_non_positive_acquisition_cost() -> None:
    with pytest.raises(ValueError):
        _fixed_asset(
            acquisition_cost=Decimal("0.00")
        )


def test_rejects_invalid_useful_life() -> None:
    with pytest.raises(ValueError):
        _fixed_asset(
            useful_life_months=0
        )


def test_rejects_depreciation_start_before_acquisition() -> None:
    with pytest.raises(ValueError):
        _fixed_asset(
            depreciation_start_date=date(
                2026,
                3,
                14,
            )
        )


def test_disposed_asset_requires_disposal_date() -> None:
    with pytest.raises(ValueError):
        _fixed_asset(
            status=FixedAssetStatus.DISPOSED
        )


def test_creates_disposed_fixed_asset() -> None:
    asset = _fixed_asset(
        status=FixedAssetStatus.DISPOSED,
        disposal_date=date(2028, 6, 30),
    )

    assert asset.status is FixedAssetStatus.DISPOSED
    assert asset.disposal_date == date(
        2028,
        6,
        30,
    )
