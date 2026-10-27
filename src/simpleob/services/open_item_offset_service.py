"""Atomare manuelle Verrechnung von Guthaben- und Rechnungs-OPs."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_offset import (
    CreditOffsetSummary,
    InvoiceOffsetSummary,
    OffsetDirection,
    OpenItemOffset,
)


class OpenItemOffsetService:
    """Verrechnet genau einen Rechnungs-OP mit genau einem Guthaben-OP."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        offset_repository: OpenItemOffsetRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._offset_repository = offset_repository

    def list_open_invoices(
        self, *, company_id: UUID, partner_id: UUID, direction: OffsetDirection
    ) -> tuple[InvoiceOffsetSummary, ...]:
        return self._offset_repository.list_open_invoices(
            company_id=company_id,
            partner_id=partner_id,
            direction=direction,
        )

    def list_open_credits(
        self, *, company_id: UUID, partner_id: UUID, direction: OffsetDirection
    ) -> tuple[CreditOffsetSummary, ...]:
        return self._offset_repository.list_open_credits(
            company_id=company_id,
            partner_id=partner_id,
            direction=direction,
        )

    def post_offset(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        direction: OffsetDirection,
        invoice_open_item_id: UUID,
        credit_open_item_id: UUID,
        amount: Decimal,
        settlement_date: date,
        booking_date: date,
        description: str | None = None,
        settlement_id: UUID | None = None,
        invoice_event_id: UUID | None = None,
        credit_event_id: UUID | None = None,
    ) -> OpenItemOffset:
        try:
            if not isinstance(direction, OffsetDirection):
                raise TypeError("direction must be an OffsetDirection")
            amount = to_decimal(amount)
            if amount <= ZERO:
                raise ValueError("Der Verrechnungsbetrag muss größer als 0,00 sein.")
            invoice = self._offset_repository.get_invoice(
                company_id=company_id,
                partner_id=partner_id,
                open_item_id=invoice_open_item_id,
                direction=direction,
                for_update=True,
            )
            credit = self._offset_repository.get_credit(
                company_id=company_id,
                partner_id=partner_id,
                open_item_id=credit_open_item_id,
                direction=direction,
                for_update=True,
            )
            if invoice is None or credit is None:
                raise ValueError("Ein zu verrechnender OP ist nicht vorhanden.")
            self._offset_repository.ensure_invoice_not_cancelled(
                open_item_id=invoice_open_item_id,
                direction=direction,
            )
            if invoice.partner_id != credit.partner_id or invoice.partner_id != partner_id:
                raise ValueError("Rechnungs-OP und Guthaben-OP müssen demselben Geschäftspartner gehören.")
            if invoice.direction is not credit.direction or invoice.direction is not direction:
                raise ValueError("Guthaben und Rechnungs-OP passen fachlich nicht zusammen.")
            if invoice.open_amount <= ZERO:
                raise ValueError("Der Rechnungs-OP ist bereits vollständig ausgeglichen.")
            if credit.available_amount <= ZERO:
                raise ValueError("Das Guthaben ist bereits vollständig verbraucht.")
            if amount > invoice.open_amount:
                raise ValueError("Der Verrechnungsbetrag übersteigt den offenen Rechnungsbetrag.")
            if amount > credit.available_amount:
                raise ValueError("Der Verrechnungsbetrag übersteigt das verfügbare Guthaben.")

            if direction is OffsetDirection.CUSTOMER:
                debit_account = credit.account_number
                credit_account = invoice.account_number
                debit_side = EntrySide.DEBIT
                credit_side = EntrySide.CREDIT
            else:
                debit_account = invoice.account_number
                credit_account = credit.account_number
                debit_side = EntrySide.DEBIT
                credit_side = EntrySide.CREDIT
            booking = Booking(
                booking_date=booking_date,
                description=description,
                lines=(
                    BookingLine(debit_account, debit_side, amount),
                    BookingLine(credit_account, credit_side, amount),
                ),
            )
            offset = OpenItemOffset(
                company_id=company_id,
                partner_id=partner_id,
                direction=direction,
                invoice_open_item_id=invoice_open_item_id,
                credit_open_item_id=credit_open_item_id,
                amount=amount,
                settlement_date=settlement_date,
                booking_id=booking.booking_id,
                **(
                    {"settlement_id": settlement_id}
                    if settlement_id is not None
                    else {}
                ),
                **(
                    {"invoice_event_id": invoice_event_id}
                    if invoice_event_id is not None
                    else {}
                ),
                **(
                    {"credit_event_id": credit_event_id}
                    if credit_event_id is not None
                    else {}
                ),
            )
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._offset_repository.add(
                offset=offset,
                fiscal_year=fiscal_year,
                commit=False,
            )
            self._booking_repository.commit()
            return offset
        except Exception:
            self._booking_repository.rollback()
            raise
