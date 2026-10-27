"""Werte der aktuellen, rein lesenden OP-Übersicht."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class OpenItemKind(StrEnum):
    CUSTOMER_RECEIVABLE = "CUSTOMER_RECEIVABLE"
    SUPPLIER_PAYABLE = "SUPPLIER_PAYABLE"
    CUSTOMER_CREDIT = "CUSTOMER_CREDIT"
    SUPPLIER_CREDIT = "SUPPLIER_CREDIT"

    @property
    def label(self) -> str:
        return {
            OpenItemKind.CUSTOMER_RECEIVABLE: "Kundenforderung",
            OpenItemKind.SUPPLIER_PAYABLE: "Lieferantenverbindlichkeit",
            OpenItemKind.CUSTOMER_CREDIT: "Kundenguthaben",
            OpenItemKind.SUPPLIER_CREDIT: "Lieferantenguthaben",
        }[self]


class OpenItemActivityKind(StrEnum):
    ORIGINAL = "ORIGINAL"
    PAYMENT = "PAYMENT"
    OFFSET = "OFFSET"
    PAYMENT_CORRECTION = "PAYMENT_CORRECTION"
    INVOICE_CANCELLATION = "INVOICE_CANCELLATION"

    @property
    def label(self) -> str:
        return {
            OpenItemActivityKind.ORIGINAL: "Ursprungsbeleg",
            OpenItemActivityKind.PAYMENT: "Zahlungszuordnung",
            OpenItemActivityKind.OFFSET: "Verrechnung",
            OpenItemActivityKind.PAYMENT_CORRECTION: (
                "Korrektur der Zahlungszuordnung"
            ),
            OpenItemActivityKind.INVOICE_CANCELLATION: "Rechnungsstorno",
        }[self]


@dataclass(frozen=True, slots=True)
class OpenItemPartnerOption:
    partner_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class OpenItemOverviewItem:
    company_id: UUID
    partner_id: UUID
    partner_name: str
    open_item_id: UUID
    kind: OpenItemKind
    document_number: str
    document_date: date
    booking_date: date
    due_date: date | None
    original_amount: Decimal
    payments_amount: Decimal
    offsets_amount: Decimal
    open_amount: Decimal
    source_booking_id: str


@dataclass(frozen=True, slots=True)
class OpenItemOverviewReport:
    company_id: UUID
    partners: tuple[OpenItemPartnerOption, ...]
    items: tuple[OpenItemOverviewItem, ...]
    include_settled: bool


@dataclass(frozen=True, slots=True)
class OpenItemActivity:
    kind: OpenItemActivityKind
    activity_date: date
    booking_date: date | None
    amount: Decimal
    reference: str
    description: str
    booking_id: str | None = None
    payment_id: str | None = None
    recorded_at: datetime | None = None
    payment_total: Decimal | None = None


@dataclass(frozen=True, slots=True)
class OpenItemOverviewDetail:
    item: OpenItemOverviewItem
    activities: tuple[OpenItemActivity, ...]
