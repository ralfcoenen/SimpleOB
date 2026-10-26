"""Atomare Haupt- und Nebenbuchung einer Rechnungsteil- oder Vollzahlung."""

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
    """Bucht tatsächliche Zahlungen und ordnet sie einzelnen Rechnungs-OPs zu."""

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
        try:
            if not isinstance(direction, PaymentDirection):
                raise TypeError("direction must be a PaymentDirection")
            amount = to_decimal(amount)
            if amount <= ZERO:
                raise ValueError("Der Zahlungsbetrag muss größer als 0,00 sein.")
            invoice = self._payment_repository.get_open_invoice(
                company_id=company_id,
                open_item_id=open_item_id,
                direction=direction,
                for_update=True,
            )
            if invoice is None:
                raise ValueError("Der Rechnungs-OP ist nicht vorhanden.")
            if invoice.partner_id != partner_id:
                raise ValueError(
                    "Der Rechnungs-OP gehört zu einem anderen Geschäftspartner."
                )
            if invoice.open_amount <= ZERO:
                raise ValueError("Der Rechnungs-OP ist bereits vollständig ausgeglichen.")
            if amount > invoice.open_amount:
                raise ValueError(
                    f"Die Zahlung übersteigt den offenen Rechnungsbetrag "
                    f"({invoice.open_amount:.2f}). Überzahlungen sind in dieser "
                    "Stufe nicht zulässig."
                )

            roles = self._chart_of_accounts_repository.load_account_roles(company_id)
            if roles is None:
                raise ValueError("Für den Mandanten sind keine Kontenrollen konfiguriert.")
            if direction is PaymentDirection.CUSTOMER_RECEIPT:
                if len(roles.customer_receivables) != 1:
                    raise ValueError(
                        "Für den Mandanten muss genau ein Kundenforderungskonto "
                        "konfiguriert sein."
                    )
                invoice_account = next(iter(roles.customer_receivables))
                self._chart_of_accounts_repository.validate_customer_receivable_account(
                    company_id=company_id,
                    account_number=invoice_account,
                )
            else:
                if len(roles.supplier_payables) != 1:
                    raise ValueError(
                        "Für den Mandanten muss genau ein Lieferantenverbindlichkeitskonto "
                        "konfiguriert sein."
                    )
                invoice_account = next(iter(roles.supplier_payables))
                self._chart_of_accounts_repository.validate_supplier_payable_account(
                    company_id=company_id,
                    account_number=invoice_account,
                )
            self._chart_of_accounts_repository.validate_payment_cash_bank_account(
                company_id=company_id,
                account_number=cash_bank_account_number,
            )

            if direction is PaymentDirection.CUSTOMER_RECEIPT:
                lines = (
                    BookingLine(
                        account_number=cash_bank_account_number,
                        side=EntrySide.DEBIT,
                        amount=amount,
                    ),
                    BookingLine(
                        account_number=invoice_account,
                        side=EntrySide.CREDIT,
                        amount=amount,
                    ),
                )
            else:
                lines = (
                    BookingLine(
                        account_number=invoice_account,
                        side=EntrySide.DEBIT,
                        amount=amount,
                    ),
                    BookingLine(
                        account_number=cash_bank_account_number,
                        side=EntrySide.CREDIT,
                        amount=amount,
                    ),
                )
            booking = Booking(
                booking_date=booking_date,
                voucher_no=voucher_no,
                description=description,
                lines=lines,
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
            event = OpenItemPaymentEvent(
                payment_id=payment.payment_id,
                open_item_id=open_item_id,
                direction=direction,
                amount=amount,
                effective_date=payment_date,
                **({"event_id": event_id} if event_id is not None else {}),
            )
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._payment_repository.add(
                payment=payment,
                event=event,
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
