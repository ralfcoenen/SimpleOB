"""Integrationstests für Gutschriften und Guthaben-OPs."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.credit_note_repository import CreditNoteRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    GuthabenOP,
    GuthabenOPEreignis,
    Gutschrift,
    Kontenrolle,
    Konto,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.database.receivable_invoice_repository import (
    ReceivableInvoiceRepository,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.credit_note import (
    CreditNoteKind,
    DuplicateSupplierCreditNoteError,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.credit_note_posting_service import CreditNotePostingService
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")
ITEMS = (VatBookingItem("4000", Decimal("119.00"), 19),)


def _environment(*, customer_credit_type=AccountType.LIABILITY.name,
                 supplier_credit_type=AccountType.ASSET.name):
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "Gutschriften Test UG")
    company_repository = CompanyRepository(session)
    company_repository.add(company)
    company_repository.add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(
        company_id=str(company.company_id)
    ).one()
    session.query(Wirtschaftsjahr).one().status = FiscalYearStatus.OPEN.value
    session.add_all(
        (
            Konto(
                mandant_id=mandate.id,
                account_number="2400",
                name="Kundenguthaben",
                account_type=customer_credit_type,
                is_active=True,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="1300",
                name="Lieferantenguthaben",
                account_type=supplier_credit_type,
                is_active=True,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="1100",
                name="Forderungen",
                account_type=AccountType.ASSET.name,
                is_active=True,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="4000",
                name="Erlöse",
                account_type=AccountType.REVENUE.name,
                is_active=True,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="6100",
                name="Aufwendungen",
                account_type=AccountType.EXPENSE.name,
                is_active=True,
            ),
        )
    )
    session.add_all(
        (
            Kontenrolle(
                mandant_id=mandate.id,
                role="CUSTOMER_CREDIT_BALANCES",
                account_number="2400",
            ),
            Kontenrolle(
                mandant_id=mandate.id,
                role="SUPPLIER_CREDIT_BALANCES",
                account_number="1300",
            ),
            Kontenrolle(
                mandant_id=mandate.id,
                role="CUSTOMER_RECEIVABLES",
                account_number="1100",
            ),
        )
    )
    session.commit()
    partner_repository = BusinessPartnerRepository(session)
    partner = BusinessPartner(
        company_id=company.company_id,
        name="Kunde und Lieferant GmbH",
        is_customer=True,
        is_supplier=True,
    )
    partner_repository.add(partner)
    booking_repository = BookingRepository(session)
    credit_note_repository = CreditNoteRepository(session)
    service = CreditNotePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        credit_note_repository=credit_note_repository,
        chart_of_accounts_repository=ChartOfAccountsRepository(session),
    )
    return engine, session, company, partner, service


def _post(service, company, partner, kind, *, note_number="GS-001", **kwargs):
    method = (
        service.post_customer_credit_note
        if kind is CreditNoteKind.CUSTOMER
        else service.post_supplier_credit_note
    )
    return method(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        note_number=note_number,
        note_date=date(2026, 6, 10),
        items=(
            (VatBookingItem("4000", Decimal("119.00"), 19),)
            if kind is CreditNoteKind.CUSTOMER
            else (VatBookingItem("6100", Decimal("119.00"), 19),)
        ),
        vat_accounts=VAT,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("kind", "account_number", "side"),
    [
        (CreditNoteKind.CUSTOMER, "2400", "CREDIT"),
        (CreditNoteKind.SUPPLIER, "1300", "DEBIT"),
    ],
)
def test_credit_note_creates_one_booking_and_one_credit_open_item(
    kind, account_number, side
):
    engine, session, company, partner, service = _environment()
    try:
        chart = ChartOfAccountsRepository(session)
        loaded = chart.load_account_roles(company.company_id)
        roles = AccountingAccountRoles(
            cash_accounts=loaded.cash_accounts,
            bank_accounts=loaded.bank_accounts,
            general_rate_sales_accounts=loaded.general_rate_sales_accounts,
            customer_receivables=loaded.customer_receivables,
            supplier_payables=loaded.supplier_payables,
            customer_credit_balances=loaded.customer_credit_balances,
            supplier_credit_balances=loaded.supplier_credit_balances,
        )
        chart.save_account_roles(company_id=company.company_id, account_roles=roles)

        note = _post(service, company, partner, kind)
        booking = session.query(Buchung).one()
        model = session.query(Gutschrift).one()
        open_item = session.query(GuthabenOP).one()
        assert session.query(Buchung).count() == 1
        assert session.query(Gutschrift).count() == 1
        assert session.query(GuthabenOP).count() == 1
        assert model.credit_note_id == str(note.credit_note_id)
        assert model.partner_id == str(partner.partner_id)
        assert model.note_number == "GS-001"
        assert model.note_date == date(2026, 6, 10)
        assert model.booking_id == booking.booking_id == str(note.booking_id)
        line = next(
            line for line in booking.zeilen
            if line.account_number == account_number
        )
        assert line.side == side
        assert line.amount == open_item.amount == Decimal("119.00")
        assert open_item.amount == Decimal("119.00")
        open_item_id = UUID(open_item.open_item_id)
        assert service._credit_note_repository.get_open_amount(
            open_item_id
        ) == Decimal("119.00")
        session.add(
            GuthabenOPEreignis(
                event_id=str(uuid4()),
                open_item_id=open_item.open_item_id,
                effective_date=date(2026, 7, 1),
                amount_delta=Decimal("-20.00"),
            )
        )
        session.commit()
        assert service._credit_note_repository.get_open_amount(
            open_item_id
        ) == Decimal("99.00")
    finally:
        session.close()
        engine.dispose()


def test_failure_after_staging_rolls_back_booking_note_and_open_item():
    engine, session, company, partner, service = _environment()

    class FailingRepository(CreditNoteRepository):
        def add(self, **kwargs):
            super().add(**kwargs)
            raise RuntimeError("simulierter Guthaben-OP-Fehler")

    service._credit_note_repository = FailingRepository(session)
    try:
        with pytest.raises(RuntimeError, match="Guthaben-OP-Fehler"):
            _post(service, company, partner, CreditNoteKind.CUSTOMER)
        assert session.query(Buchung).count() == 0
        assert session.query(Gutschrift).count() == 0
        assert session.query(GuthabenOP).count() == 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("kind", "wrong_customer_type", "wrong_supplier_type"),
    [
        (CreditNoteKind.CUSTOMER, AccountType.ASSET.name, AccountType.ASSET.name),
        (
            CreditNoteKind.SUPPLIER,
            AccountType.LIABILITY.name,
            AccountType.LIABILITY.name,
        ),
    ],
)
def test_credit_balance_role_requires_correct_account_type(
    kind, wrong_customer_type, wrong_supplier_type
):
    engine, session, company, partner, service = _environment(
        customer_credit_type=wrong_customer_type,
        supplier_credit_type=wrong_supplier_type,
    )
    try:
        with pytest.raises(ValueError, match="muss ein"):
            _post(service, company, partner, kind)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_foreign_partner_is_rejected_and_invoice_reference_is_persisted():
    engine, session, company, partner, service = _environment()
    other_company = Company(uuid4(), "Fremdmandant")
    CompanyRepository(session).add(other_company)
    foreign_partner = BusinessPartner(
        company_id=other_company.company_id,
        name="Fremdkunde",
        is_customer=True,
        is_supplier=False,
    )
    BusinessPartnerRepository(session).add(foreign_partner)
    try:
        with pytest.raises(ValueError, match="gehört nicht zum geöffneten Mandanten"):
            service.post_customer_credit_note(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=foreign_partner.partner_id,
                note_number="GS-FREM",
                note_date=date(2026, 6, 10),
                items=(VatBookingItem("4000", Decimal("10.00"), 0),),
                vat_accounts=VAT,
            )
        assert session.query(Buchung).count() == 0

        receivable_service = ReceivableInvoicePostingService(
            booking_repository=BookingRepository(session),
            partner_repository=BusinessPartnerRepository(session),
            invoice_repository=ReceivableInvoiceRepository(session),
            chart_of_accounts_repository=ChartOfAccountsRepository(session),
        )
        receivable_service.post_output_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            invoice_number="AR-100",
            booking_date=date(2026, 5, 1),
            due_date=date(2026, 5, 31),
            items=(VatBookingItem("4000", Decimal("119.00"), 19),),
            vat_accounts=VAT,
        )
        with pytest.raises(ValueError, match="bereits vergeben"):
            _post(
                service,
                company,
                partner,
                CreditNoteKind.CUSTOMER,
                note_number="AR-100",
            )
        assert session.query(Buchung).count() == 1
        note = _post(
            service,
            company,
            partner,
            CreditNoteKind.CUSTOMER,
            note_number="GS-100",
            original_invoice_number="AR-100",
        )
        stored = session.query(Gutschrift).filter_by(
            credit_note_id=str(note.credit_note_id)
        ).one()
        original = session.query(Ausgangsrechnung).filter_by(
            invoice_number="AR-100"
        ).one()
        assert stored.original_receivable_invoice_id == original.invoice_id
        assert stored.original_payable_invoice_id is None
    finally:
        session.close()
        engine.dispose()


def test_duplicate_document_numbers_follow_customer_and_supplier_rules():
    engine, session, company, partner, service = _environment()
    try:
        _post(service, company, partner, CreditNoteKind.CUSTOMER)
        with pytest.raises(ValueError, match="bereits vergeben"):
            _post(service, company, partner, CreditNoteKind.CUSTOMER)
        assert session.query(Buchung).count() == 1

        _post(service, company, partner, CreditNoteKind.SUPPLIER)
        with pytest.raises(DuplicateSupplierCreditNoteError):
            _post(service, company, partner, CreditNoteKind.SUPPLIER)
        assert session.query(Buchung).count() == 2
        accepted = _post(
            service,
            company,
            partner,
            CreditNoteKind.SUPPLIER,
            duplicate_reason="Gutschrift wurde vom Lieferanten erneut übersandt.",
        )
        stored = session.query(Gutschrift).filter_by(
            credit_note_id=str(accepted.credit_note_id)
        ).one()
        assert stored.duplicate_reason == (
            "Gutschrift wurde vom Lieferanten erneut übersandt."
        )
        assert session.query(Gutschrift).count() == 3
        assert session.query(GuthabenOP).count() == 3
    finally:
        session.close()
        engine.dispose()
