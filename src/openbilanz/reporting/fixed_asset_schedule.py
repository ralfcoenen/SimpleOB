"""Aggregierter Anlagenspiegel."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FixedAssetScheduleRow:
    """Aggregierte Werte einer Anlageklasse."""

    position_code: str
    opening_cost: Decimal
    additions: Decimal
    disposals: Decimal
    current_depreciation: Decimal
    accumulated_depreciation: Decimal
    closing_book_value: Decimal


@dataclass(frozen=True, slots=True)
class FixedAssetSchedule:
    """Anlagenspiegel eines Geschäftsjahres."""

    rows: tuple[FixedAssetScheduleRow, ...]
