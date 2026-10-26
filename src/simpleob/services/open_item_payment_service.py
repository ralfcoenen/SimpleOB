"""Atomare Haupt- und Nebenbuchung tatsächlicher Rechnungszahlungen."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_payment import (
    OpenItemPayment,
    OpenItemPaymentEvent,
    PaymentDirection,
)


class OpenItemPaymentService:
    """Bucht eine Zahlung und ordnet sie einem oder mehreren Rechnungs-OPs zu."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        payment_repository: OpenItemPaymentRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._payment_repository = payment_repository
        self._chart_of_accounts_repository = chart_of_accounts_repository

    def list_open_invoices(self, company_id: UUID):
        return self._payment_repository.list_open_invoices(company_id)

    def payment_account_numbers(self, company_id: UUID) -> frozenset[str]:
        roles = self._chart_of_accounts_repository.load_account_roles(company_id)
        if roles is None:
            return frozenset()
        return roles.cash_accounts | roles.bank_accounts

    def post_payment(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        open_item_id: UUID,
        direction: PaymentDirection,
        amount: Decimal,
        payment_date: date,
        booking_date: date,
        cash_bank_account_number: str,
        voucher_no: str | None = None,
        description: str | None = None,
        payment_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> OpenItemPayment:
        """Kompatibler Einzelzahlungsweg aus Stufe 3A."""
        return self.post_payment_allocations(
            company_id=company_id,
            fiscal_year=fiscal_year,
            partner_id=partner_id,
            direction=direction,
            amount=amount,
            allocations=((open_item_id, amount),),
            payment_date=payment_date,
            booking_date=booking_date,
            cash_bank_account_number=cash_bank_account_number,
            voucher_no=voucher_no,
            description=description,
            payment_id=payment_id,
            event_ids=(event_id,) if event_id is not None else None,
        )

    def post_payment_allocations(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        direction: PaymentDirection,
        amount: Decimal,
        allocations: tuple[tuple[UUID, Decimal], ...],
        payment_date: date,
        booking_date: date,
        cash_bank_account_number: str,
        voucher_no: str | None = None,
        description: str | None = None,
        payment_id: UUID | None = None,
        event_ids: tuple[UUID, ...] | None = None,
    ) -> OpenItemPayment:
        """Bucht eine Zahlung mit expliziten Zuordnungen zu mehreren Rechnungs-OPs."""
        try:
            if not isinstance(direction, PaymentDirection):
                raise TypeError("direction must be a PaymentDirection")
            amount = to_decimal(amount)
            if amount <= ZERO:
                raise ValueError("Der Zahlungsbetrag muss größer als 0,00 sein.")
            if not allocations:
                raise ValueError("Mindestens ein Rechnungs-OP muss zugeordnet werden.")
            if event_ids is not None and len(event_ids) != len(allocations):
                raise ValueError("Für jede Zuordnung muss genau eine Ereignis-ID vorliegen.")

            normalized: list[tuple[UUID, Decimal]] = []
            seen_open_item_ids: set[UUID] = set()
            for open_item_id, raw_allocation_amount in allocations:
                if not isinstance(open_item_id, UUID):
                    raise TypeError("open_item_id muss eine UUID sein.")
                if open_item_id in seen_open_item_ids:
                    raise ValueError("Ein Rechnungs-OP darf pro Zahlung nur einmal zugeordnet werden.")
                seen_open_item_ids.add(open_item_id)
                allocation_amount = to_decimal(raw_allocation_amount)
                if allocation_amount <= ZERO:
                    raise ValueError("Jeder Zuordnungsbetrag muss größer als 0,00 sein.")
                normalized.append((open_item_id, allocation_amount))
            if sum((allocation for _, allocation in normalized), start=ZERO) != amount:
                raise ValueError("Die Summe der OP-Zuordnungen muss exakt dem Zahlungsbetrag entsprechen.")

            for open_item_id, allocation_amount in sorted(
                normalized, key=lambda allocation: str(allocation[0])
            ):
                invoice = self._payment_repository.get_open_invoice(
                    company_id=company_id,
                    open_item_id=open_item_id,
                    direction=direction,
                    for_update=True,
                )
                if invoice is None:
                    raise ValueError("Ein Rechnungs-OP ist nicht vorhanden.")
                if invoice.partner_id != partner_id:
                    raise ValueError("Alle Rechnungs-OPs müssen demselben Geschäftspartner gehören.")
                if invoice.open_amount <= ZERO:
                    raise ValueError("Ein Rechnungs-OP ist bereits vollständig ausgeglichen.")
                if allocation_amount > invoice.open_amount:
                    raise ValueError(
                        "Eine Zuordnung übersteigt den offenen Rechnungsbetrag "
                        f"({invoice.document_number}: {invoice.open_amount:.2f})."
                    )
            roles = self._chart_of_accounts_repository.load_account_roles(company_id)
            if roles is None:
                raise ValueError("Für den Mandanten sind keine Kontenrollen konfiguriert.")
            if direction is PaymentDirection.CUSTOMER_RECEIPT:
                if len(roles.customer_receivables) != 1:
                    raise ValueError(
                        "Für den Mandanten muss genau ein Kundenforderungskonto konfiguriert sein."
                    )
                invoice_account = next(iter(roles.customer_receivables))
                self._chart_of_accounts_repository.validate_customer_receivable_account(
                    company_id=company_id,
                    account_number=invoice_account,
                )
                control_side = EntrySide.CREDIT
                cash_side = EntrySide.DEBIT
            else:
                if len(roles.supplier_payables) != 1:
                    raise ValueError(
                        "Für den Mandanten muss genau ein Lieferantenverbindlichkeitskonto konfiguriert sein."
                    )
                invoice_account = next(iter(roles.supplier_payables))
                self._chart_of_accounts_repository.validate_supplier_payable_account(
                    company_id=company_id,
                    account_number=invoice_account,
                )
                control_side = EntrySide.DEBIT
                cash_side = EntrySide.CREDIT
            self._chart_of_accounts_repository.validate_payment_cash_bank_account(
                company_id=company_id,
                account_number=cash_bank_account_number,
            )

            lines = [
                BookingLine(
                    account_number=cash_bank_account_number,
                    side=cash_side,
                    amount=amount,
                )
            ]
            lines.extend(
                BookingLine(
                    account_number=invoice_account,
                    side=control_side,
                    amount=allocation_amount,
                )
                for _, allocation_amount in normalized
            )
            booking = Booking(
                booking_date=booking_date,
                voucher_no=voucher_no,
                description=description,
                lines=tuple(lines),
            )
            payment = OpenItemPayment(
                company_id=company_id,
                partner_id=partner_id,
                direction=direction,
                amount=amount,
                payment_date=payment_date,
                booking_id=booking.booking_id,
                **({"payment_id": payment_id} if payment_id is not None else {}),
            )
            events = tuple(
                OpenItemPaymentEvent(
                    payment_id=payment.payment_id,
                    open_item_id=open_item_id,
                    direction=direction,
                    amount=allocation_amount,
                    effective_date=payment_date,
                    **(
                        {"event_id": event_ids[index]}
                        if event_ids is not None
                        else {}
                    ),
                )
                for index, (open_item_id, allocation_amount) in enumerate(normalized)
            )
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._payment_repository.add(
                payment=payment,
                events=events,
                fiscal_year=fiscal_year,
                company_id=company_id,
                partner_id=partner_id,
                commit=False,
            )
            self._booking_repository.commit()
            return payment
        except Exception:
            self._booking_repository.rollback()
            raise
