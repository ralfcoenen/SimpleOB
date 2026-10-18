"""Status eines Geschäftsjahres."""

from enum import Enum


class FiscalYearStatus(str, Enum):
    """Fachlicher Zustand eines Geschäftsjahres."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
 