"""Tests für Anlagenbewegungen."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)


def test_creates_acquisition_movement() -> None:
    movement = FixedAssetMovement(
        fixed_asset_id=uuid4(),
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 23),
        amount=Decimal("10000.00"),
        booking_id=uuid4(),
        movement_type=(
            FixedAssetMovementType.ACQUISITION
        ),
    )

    assert movement.amount == Decimal("10000.00")
    assert movement.reversed_movement_id is None


def test_reversal_requires_original_movement() -> None:
    with pytest.raises(
        ValueError,
        match="requires reversed_movement_id",
    ):
        FixedAssetMovement(
            fixed_asset_id=uuid4(),
            fiscal_year_end=date(2026, 12, 31),
            movement_date=date(2026, 8, 23),
            amount=Decimal("10000.00"),
            booking_id=uuid4(),
            movement_type=(
                FixedAssetMovementType.REVERSAL
            ),
        )


def test_reversal_references_original_movement() -> None:
    original_movement_id = uuid4()

    movement = FixedAssetMovement(
        fixed_asset_id=uuid4(),
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 23),
        amount=Decimal("10000.00"),
        booking_id=uuid4(),
        movement_type=(
            FixedAssetMovementType.REVERSAL
        ),
        reversed_movement_id=original_movement_id,
    )

    assert (
        movement.reversed_movement_id
        == original_movement_id
    )
