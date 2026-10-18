"""Berechnungsergebnis eines Anlagenabgangs."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.booking import Booking


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalCalculation:
    """Enthält die berechneten Werte eines Anlagenverkaufs."""

    acquisition_cost: Decimal
    accumulated_depreciation: Decimal
    carrying_amount: Decimal
    gross_proceeds: Decimal
    net_proceeds: Decimal
    tax_amount: Decimal
    gain: Decimal
    loss: Decimal
    booking: Booking
