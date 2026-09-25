"""Arten von Buchungen zur Umsetzung einer Ergebnisverwendung."""

from enum import Enum


class ProfitAppropriationPostingType(str, Enum):
    """Art einer Buchung zur Umsetzung eines Ergebnisverwendungsbeschlusses."""

    STATUTORY_RESERVE_ADDITION = "STATUTORY_RESERVE_ADDITION"
    OTHER_REVENUE_RESERVES_ADDITION = "OTHER_REVENUE_RESERVES_ADDITION"
    STATUTORY_RESERVE_RELEASE = "STATUTORY_RESERVE_RELEASE"
    OTHER_REVENUE_RESERVES_RELEASE = "OTHER_REVENUE_RESERVES_RELEASE"
    DISTRIBUTION = "DISTRIBUTION"
