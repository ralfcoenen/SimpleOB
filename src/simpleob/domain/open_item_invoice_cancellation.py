"""Werte für das vollständige Storno unbezahlter Rechnungs-OPs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.domain.booking import Booking


@dataclass(frozen=True, slots=True)
class InvoiceCancellationPreview:
    company_id: UUID
    partner_id: UUID
    partner_name: str
    invoice_id: UUID
    open_item_id: UUID
    invoice_number: str
    invoice_date: date
    invoice_booking_date: date
    amount: Decimal
    original_booking: Booking
    supplier_invoice: bool
