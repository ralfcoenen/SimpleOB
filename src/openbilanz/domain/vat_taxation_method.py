"""Zeitliche Besteuerungsart der Umsatzsteuer."""

from enum import StrEnum


class VatTaxationMethod(StrEnum):
    """Bestimmt die zeitliche Entstehung der Umsatzsteuer."""

    AGREED = "AGREED"
    RECEIVED = "RECEIVED"
