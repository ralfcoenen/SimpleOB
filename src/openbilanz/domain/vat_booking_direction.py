"""Richtung einer umsatzsteuerlichen Buchungsposition."""

from enum import StrEnum


class VatBookingDirection(StrEnum):
    """Kennzeichnet Ausgangs- oder Eingangsumsatz."""

    OUTPUT = "OUTPUT"
    INPUT = "INPUT"
