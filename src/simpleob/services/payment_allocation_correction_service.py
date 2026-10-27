"""Manuelle, begründete Korrektur einer bestehenden Zahlungszuordnung."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.database.payment_allocation_correction_repository import (
    PaymentAllocationCorrectionRepository,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.payment_allocation_correction import PaymentAllocationCorrection


class PaymentAllocationCorrectionService:
    def __init__(self, *, booking_repository: BookingRepository,
                 correction_repository: PaymentAllocationCorrectionRepository,
                 offset_repository: OpenItemOffsetRepository,
                 payment_repository: OpenItemPaymentRepository) -> None:
        self._booking = booking_repository
        self._corrections = correction_repository
        self._offsets = offset_repository
        self._payments = payment_repository

    def list_correctable_allocations(self, company_id: UUID):
        return self._corrections.list_correctable(company_id)

    def list_open_targets(self, *, company_id: UUID, partner_id: UUID, direction: PaymentDirection):
        return tuple(
            invoice for invoice in self._payments.list_open_invoices(company_id)
            if invoice.partner_id == partner_id and invoice.direction is direction
        )

    def correct(self, *, company_id: UUID, fiscal_year: FiscalYear, original_event_id: UUID,
                target_open_item_id: UUID, amount: Decimal, correction_date: date,
                booking_date: date, reason: str, confirmed: bool) -> PaymentAllocationCorrection:
        try:
            if not confirmed:
                raise ValueError("Die Korrektur muss ausdrücklich bestätigt werden.")
            if not reason or not reason.strip():
                raise ValueError("Eine Begründung für die Korrektur ist erforderlich.")
            amount = to_decimal(amount)
            if amount <= ZERO:
                raise ValueError("Der Korrekturbetrag muss größer als 0,00 sein.")
            source = self._corrections.get_correctable(company_id=company_id, event_id=original_event_id)
            if source is None:
                raise ValueError("Die ursprüngliche Zahlungszuordnung ist nicht vorhanden.")
            self._payments.ensure_not_cancelled(
                open_item_id=source.source_open_item_id,
                direction=source.direction,
            )
            if target_open_item_id == source.source_open_item_id:
                raise ValueError("Quell- und Zielrechnung müssen unterschiedlich sein.")
            if amount > source.correctable_amount:
                raise ValueError("Der Betrag übersteigt den noch korrigierbaren Anteil der Zuordnung.")
            direction = OffsetDirection.CUSTOMER if source.direction is PaymentDirection.CUSTOMER_RECEIPT else OffsetDirection.SUPPLIER
            source_invoice = self._offsets.get_invoice(company_id=company_id, partner_id=source.partner_id,
                open_item_id=source.source_open_item_id, direction=direction, for_update=True)
            target_invoice = self._offsets.get_invoice(company_id=company_id, partner_id=source.partner_id,
                open_item_id=target_open_item_id, direction=direction, for_update=True)
            if source_invoice is None or target_invoice is None:
                raise ValueError("Quell- oder Zielrechnung ist nicht vorhanden.")
            self._payments.ensure_not_cancelled(
                open_item_id=target_open_item_id,
                direction=source.direction,
            )
            if target_invoice.open_amount < amount:
                raise ValueError("Der offene Betrag der Zielrechnung reicht nicht aus.")
            booking_id = None
            if source_invoice.account_number != target_invoice.account_number:
                if direction is OffsetDirection.CUSTOMER:
                    lines = (BookingLine(source_invoice.account_number, EntrySide.DEBIT, amount),
                             BookingLine(target_invoice.account_number, EntrySide.CREDIT, amount))
                else:
                    lines = (BookingLine(target_invoice.account_number, EntrySide.DEBIT, amount),
                             BookingLine(source_invoice.account_number, EntrySide.CREDIT, amount))
                booking = Booking(booking_date=booking_date, description=f"Korrektur Zahlungszuordnung: {reason.strip()}", lines=lines)
                self._booking.add(company_id=company_id, fiscal_year=fiscal_year, booking=booking, commit=False)
                booking_id = booking.booking_id
            correction = PaymentAllocationCorrection(
                company_id=company_id, partner_id=source.partner_id, payment_id=source.payment_id,
                original_event_id=source.original_event_id, direction=source.direction,
                source_open_item_id=source.source_open_item_id, target_open_item_id=target_open_item_id,
                amount=amount, correction_date=correction_date,
                booking_date=booking_date, reason=reason, booking_id=booking_id,
            )
            self._corrections.add(correction=correction, fiscal_year=fiscal_year, commit=False)
            self._booking.commit()
            return correction
        except Exception:
            self._booking.rollback()
            raise
