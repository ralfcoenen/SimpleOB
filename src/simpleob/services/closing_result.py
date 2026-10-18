"""Ergebnis eines Jahresabschlusses."""

from dataclasses import dataclass, field
from decimal import Decimal

from simpleob.domain.booking import Booking


@dataclass(frozen=True, slots=True)
class ClosingResult:
    """Enthält die ermittelten Ergebnisse eines Jahresabschlusses."""

    net_income: Decimal
    bookings: tuple[Booking, ...] = field(default_factory=tuple)
    
