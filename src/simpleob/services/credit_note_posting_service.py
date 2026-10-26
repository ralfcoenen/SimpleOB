"""Atomare Erfassung von Kunden- und Lieferantengutschriften."""

from datetime import date
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.credit_note_repository import CreditNoteRepository
from simpleob.domain.credit_note import (
    CreditBalanceOpenItem,
    CreditNote,
    CreditNoteKind,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.vat_booking_service import VatBookingService


class CreditNotePostingService:
    """Speichert Gutschrift und Guthaben-OP zusammen mit der Buchung."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        partner_repository: BusinessPartnerRepository,
        credit_note_repository: CreditNoteRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
        vat_booking_service: VatBookingService | None = None,
    ) -> None:
        self._booking_repository = booking_repository
        self._partner_repository = partner_repository
        self._credit_note_repository = credit_note_repository
        self._chart_of_accounts_repository = chart_of_accounts_repository
        self._vat_booking_service = vat_booking_service or VatBookingService()

    def post_customer_credit_note(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        note_number: str,
        note_date: date,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        original_invoice_id: UUID | None = None,
        original_invoice_number: str | None = None,
        credit_note_id: UUID | None = None,
        open_item_id: UUID | None = None,
        description: str | None = None,
    ) -> CreditNote:
        return self._post_credit_note(
            kind=CreditNoteKind.CUSTOMER,
            company_id=company_id,
            fiscal_year=fiscal_year,
            partner_id=partner_id,
            note_number=note_number,
            note_date=note_date,
            items=items,
            vat_accounts=vat_accounts,
            original_invoice_id=original_invoice_id,
            original_invoice_number=original_invoice_number,
            credit_note_id=credit_note_id,
            open_item_id=open_item_id,
            description=description,
        )

    def post_supplier_credit_note(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        note_number: str,
        note_date: date,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        original_invoice_id: UUID | None = None,
        original_invoice_number: str | None = None,
        duplicate_reason: str | None = None,
        credit_note_id: UUID | None = None,
        open_item_id: UUID | None = None,
        description: str | None = None,
    ) -> CreditNote:
        return self._post_credit_note(
            kind=CreditNoteKind.SUPPLIER,
            company_id=company_id,
            fiscal_year=fiscal_year,
            partner_id=partner_id,
            note_number=note_number,
            note_date=note_date,
            items=items,
            vat_accounts=vat_accounts,
            original_invoice_id=original_invoice_id,
            original_invoice_number=original_invoice_number,
            duplicate_reason=duplicate_reason,
            credit_note_id=credit_note_id,
            open_item_id=open_item_id,
            description=description,
        )

    def _post_credit_note(
        self,
        *,
        kind: CreditNoteKind,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        note_number: str,
        note_date: date,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        original_invoice_id: UUID | None,
        original_invoice_number: str | None,
        duplicate_reason: str | None = None,
        credit_note_id: UUID | None,
        open_item_id: UUID | None,
        description: str | None,
    ) -> CreditNote:
        if not isinstance(note_number, str) or not note_number.strip():
            raise ValueError("Die Gutschriftnummer darf nicht leer sein.")
        partner = self._partner_repository.get(
            company_id=company_id,
            partner_id=partner_id,
        )
        is_customer = kind is CreditNoteKind.CUSTOMER
        if (
            partner is None
            or not partner.is_active
            or (is_customer and not partner.is_customer)
            or (not is_customer and not partner.is_supplier)
        ):
            role_label = "Kunde" if is_customer else "Lieferant"
            raise ValueError(
                f"Der aktive {role_label} gehört nicht zum geöffneten Mandanten."
            )

        if original_invoice_id is not None and original_invoice_number is not None:
            raise ValueError(
                "Gib Rechnungs-ID oder Rechnungsnummer als Bezug an, nicht beides."
            )
        if original_invoice_number is not None:
            original_invoice_id = (
                self._credit_note_repository.resolve_original_invoice_id(
                    company_id=company_id,
                    partner_id=partner_id,
                    kind=kind,
                    invoice_number=original_invoice_number,
                )
            )

        roles = self._chart_of_accounts_repository.load_account_roles(company_id)
        role_accounts = (
            roles.customer_credit_balances
            if is_customer and roles is not None
            else roles.supplier_credit_balances
            if roles is not None
            else frozenset()
        )
        if len(role_accounts) != 1:
            role_label = "Kundenguthabenkonto" if is_customer else "Lieferantenguthabenkonto"
            raise ValueError(
                f"Für den Mandanten muss genau ein {role_label} konfiguriert sein."
            )
        balance_account = next(iter(role_accounts))
        account_validator = (
            self._chart_of_accounts_repository.validate_customer_credit_balance_account
            if is_customer
            else self._chart_of_accounts_repository.validate_supplier_credit_balance_account
        )
        account_validator(
            company_id=company_id,
            account_number=balance_account,
        )
        if not isinstance(items, tuple) or not items:
            raise ValueError("Die Gutschrift benötigt mindestens eine Position.")
        gross_amount = sum((item.gross_amount for item in items), start=ZERO)
        builder = (
            self._vat_booking_service.build_customer_credit_note
            if is_customer
            else self._vat_booking_service.build_supplier_credit_note
        )
        booking = builder(
            booking_date=note_date,
            counter_account_number=balance_account,
            items=items,
            vat_accounts=vat_accounts,
            voucher_no=note_number.strip(),
            description=description,
        )
        note = CreditNote(
            company_id=company_id,
            partner_id=partner_id,
            kind=kind,
            note_number=note_number,
            note_date=note_date,
            gross_amount=gross_amount,
            booking_id=booking.booking_id,
            original_invoice_id=original_invoice_id,
            duplicate_reason=duplicate_reason,
            **({"credit_note_id": credit_note_id} if credit_note_id else {}),
        )
        open_item = CreditBalanceOpenItem(
            credit_note_id=note.credit_note_id,
            amount=gross_amount,
            **({"open_item_id": open_item_id} if open_item_id else {}),
        )
        try:
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._credit_note_repository.add(
                credit_note=note,
                open_item=open_item,
                fiscal_year=fiscal_year,
                commit=False,
            )
            self._booking_repository.commit()
        except Exception:
            self._booking_repository.rollback()
            raise
        return note
