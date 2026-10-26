"""Werte für die stichtagsbezogene OP-Hauptbuch-Abstimmung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UnexplainedControlMovement:
    booking_id: str
    booking_date: date
    voucher_no: str | None
    description: str | None
    side: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class UnresolvedCorrectionTiming:
    correction_id: str
    correction_date: date
    reason: str
    amount: Decimal
    source_open_item_id: str
    target_open_item_id: str


@dataclass(frozen=True, slots=True)
class OpenItemReconciliationRow:
    role: str
    role_label: str
    account_number: str | None
    account_name: str
    ledger_balance: Decimal
    open_item_balance: Decimal
    difference: Decimal
    status: str
    unexplained_movements: tuple[UnexplainedControlMovement, ...] = ()
    unresolved_correction_timings: tuple[UnresolvedCorrectionTiming, ...] = ()


@dataclass(frozen=True, slots=True)
class OpenItemReconciliationReport:
    company_id: UUID
    as_of_date: date
    rows: tuple[OpenItemReconciliationRow, ...]
