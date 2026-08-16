"""Fachliche Arten von Buchungen."""

from enum import Enum


class BookingType(str, Enum):
    """Fachliche Art einer Buchung."""

    REGULAR = "REGULAR"
    OPENING = "OPENING"
    CLOSING = "CLOSING"
