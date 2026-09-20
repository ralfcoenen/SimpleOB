"""Read Model für eine gefilterte Kontenauswertung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AccountActivityReportLine:
    """Eine Zeile der Kontenauswertung."""

    booking_date: date
    voucher_no: str
    account_number: str
    description: str
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


@dataclass(frozen=True, slots=True)
class AccountActivityReport:
    """Kontenauswertung eines einzelnen Kontos."""

    account_number: str
    lines: tuple[AccountActivityReportLine, ...]
    ending_balance: Decimal
