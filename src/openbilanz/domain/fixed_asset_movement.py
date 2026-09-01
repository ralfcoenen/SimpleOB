"""Buchungswirksame Bewegungen eines Anlageguts."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class FixedAssetMovement:
    """Eine buchungswirksame Bewegung eines Anlageguts."""

    fixed_asset_id: UUID
    fiscal_year_end: date
    movement_date: date
    amount: Decimal
    booking_id: UUID
    movement_type: FixedAssetMovementType
    movement_id: UUID = field(
        default_factory=uuid4
    )
    reversed_movement_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        if not isinstance(
            self.fiscal_year_end,
            date,
        ):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if not isinstance(
            self.movement_date,
            date,
        ):
            raise TypeError(
                "movement_date must be a date"
            )

        amount = to_decimal(
            self.amount
        )

        if amount <= Decimal("0.00"):
            raise ValueError(
                "amount must be greater than 0.00"
            )

        if not isinstance(
            self.booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if not isinstance(
            self.movement_type,
            FixedAssetMovementType,
        ):
            raise TypeError(
                "movement_type must be a "
                "FixedAssetMovementType"
            )

        if not isinstance(
            self.movement_id,
            UUID,
        ):
            raise TypeError(
                "movement_id must be a UUID"
            )

        if (
            self.reversed_movement_id is not None
            and not isinstance(
                self.reversed_movement_id,
                UUID,
            )
        ):
            raise TypeError(
                "reversed_movement_id must be "
                "a UUID or None"
            )

        if (
            self.movement_type
            is FixedAssetMovementType.REVERSAL
            and self.reversed_movement_id is None
        ):
            raise ValueError(
                "A reversal movement requires "
                "reversed_movement_id."
            )

        if (
            self.movement_type
            is not FixedAssetMovementType.REVERSAL
            and self.reversed_movement_id is not None
        ):
            raise ValueError(
                "Only a reversal movement may define "
                "reversed_movement_id."
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
