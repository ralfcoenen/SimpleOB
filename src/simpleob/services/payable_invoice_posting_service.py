"""Atomare Buchung einer Eingangsrechnung mit Verbindlichkeits-OP."""

from datetime import date
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.payable_invoice_repository import PayableInvoiceRepository
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.payable_invoice import PayableInvoice, PayableOpenItem
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.vat_booking_service import VatBookingService


class PayableInvoicePostingService:
    """Speichert Hauptbuchbuchung, Eingangsrechnung und OP atomar."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        partner_repository: BusinessPartnerRepository,
        invoice_repository: PayableInvoiceRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
        vat_booking_service: VatBookingService | None = None,
    ) -> None:
        self._booking_repository = booking_repository
        self._partner_repository = partner_repository
        self._invoice_repository = invoice_repository
        self._chart_of_accounts_repository = chart_of_accounts_repository
        self._vat_booking_service = vat_booking_service or VatBookingService()

    def post_supplier_invoice_on_account(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        invoice_number: str,
        booking_date: date,
        due_date: date,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        duplicate_reason: str | None = None,
        invoice_id: UUID | None = None,
        open_item_id: UUID | None = None,
        description: str | None = None,
    ) -> PayableInvoice:
        if not isinstance(invoice_number, str) or not invoice_number.strip():
            raise ValueError("Die Rechnungsnummer darf nicht leer sein.")
        invoice_number = invoice_number.strip()

        partner = self._partner_repository.get(
            company_id=company_id,
            partner_id=partner_id,
        )
        if partner is None or not partner.is_supplier or not partner.is_active:
            raise ValueError(
                "Der aktive Lieferant gehört nicht zum geöffneten Mandanten."
            )

        roles = self._chart_of_accounts_repository.load_account_roles(company_id)
        if roles is None or len(roles.supplier_payables) != 1:
            raise ValueError(
                "Für den Mandanten muss genau ein Lieferantenverbindlichkeitskonto "
                "konfiguriert sein."
            )
        payable_account = next(iter(roles.supplier_payables))
        self._chart_of_accounts_repository.validate_supplier_payable_account(
            company_id=company_id,
            account_number=payable_account,
        )

        if not isinstance(items, tuple) or not items:
            raise ValueError("Die Rechnung benötigt mindestens eine Position.")
        gross_amount = sum((item.gross_amount for item in items), start=ZERO)
        booking = self._vat_booking_service.build_input_booking(
            booking_date=booking_date,
            counter_account_number=payable_account,
            items=items,
            vat_accounts=vat_accounts,
            voucher_no=invoice_number,
            description=description,
        )
        invoice = PayableInvoice(
            company_id=company_id,
            partner_id=partner_id,
            invoice_number=invoice_number,
            invoice_date=booking_date,
            due_date=due_date,
            gross_amount=gross_amount,
            booking_id=booking.booking_id,
            duplicate_reason=duplicate_reason,
            **({"invoice_id": invoice_id} if invoice_id is not None else {}),
        )
        open_item = PayableOpenItem(
            invoice_id=invoice.invoice_id,
            amount=gross_amount,
            **({"open_item_id": open_item_id} if open_item_id is not None else {}),
        )

        try:
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._invoice_repository.add(
                invoice=invoice,
                open_item=open_item,
                fiscal_year=fiscal_year,
                commit=False,
            )
            self._booking_repository.commit()
        except Exception:
            self._booking_repository.rollback()
            raise

        return invoice
