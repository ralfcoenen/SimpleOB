"""Umsatzsteuerliche Besteuerungsart."""

from enum import Enum


class VatTaxationType(Enum):
    """Umsatzsteuerliche Behandlung eines Mandanten."""

    STANDARD = "STANDARD"
    SMALL_BUSINESS = "SMALL_BUSINESS"
