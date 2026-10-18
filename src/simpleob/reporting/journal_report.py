"""Read Model für eine gefilterte Journalauswertung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.domain.entry_side import EntrySide


@dataclass(frozen=True, slots=True)
class JournalReportLine:
    """Eine Buchungszeile des Journalberichts."""

    booking_id: UUID
    booking_number: int
    booking_date: date
    voucher_no: str
    description: str
    account_number: str
    side: EntrySide
    amount: Decimal


@dataclass(frozen=True, slots=True)
class JournalReport:
    """Journal für einen Berichtszeitraum."""

    start_date: date
    end_date: date
    lines: tuple[JournalReportLine, ...]
    