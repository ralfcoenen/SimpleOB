"""Werte für das vollständige Storno unbezahlter Rechnungs-OPs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.domain.booking import Booking


@dataclass(frozen=True, slots=True)
class InvoiceCancellationPaymentAssessment:
    """Prüfergebnis für spätere Stornos mit Zahlungshistorie.

    Das Ergebnis erlaubt noch keine Stornierung; es fasst nur die geprüfte
    Zahlungszuordnung und ihre Buchungsdatumsgrenze zusammen.
    """

    company_id: UUID
    partner_id: UUID
    open_item_id: UUID
    invoice_number: str
    invoice_amount: Decimal
    payment_event_amount: Decimal
    correction_delta: Decimal
    effective_payment_amount: Decimal
    open_amount: Decimal
    latest_payment_booking_date: date | None
    latest_correction_booking_date: date | None
    latest_required_booking_date: date | None
    payment_event_count: int
    correction_count: int


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
