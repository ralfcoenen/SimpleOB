"""Ergebnis eines Jahresabschlusses."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ClosingResult:
    """Enthält die ermittelten Ergebnisse eines Jahresabschlusses."""

    net_income: Decimal
    
