"""Integrationstests für Eingangsrechnungen auf Ziel."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Buchung,
    Eingangsrechnung,
    Kontenrolle,
    Konto,
    Mandant,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.database.payable_invoice_repository import PayableInvoiceRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.payable_invoice import DuplicateSupplierInvoiceError
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.payable_invoice_posting_service import (
    PayableInvoicePostingService,
)

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")
ITEMS = (VatBookingItem("6100", Decimal("119.00"), 19),)


def _environment(
    *,
    payable_type: str = AccountType.LIABILITY.name,
    payable_active: bool = True,
):
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "Lieferanten Test UG")
    CompanyRepository(session).add(company)
    CompanyRepository(session).add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(
        company_id=str(company.company_id)
    ).one()
    fiscal_year = session.query(Wirtschaftsjahr).one()
    fiscal_year.status = FiscalYearStatus.OPEN.value
    session.add_all(
        (
            Konto(
                mandant_id=mandate.id,
                account_number="3300",
                name="Lieferantenverbindlichkeiten",
                account_type=payable_type,
                is_active=payable_active,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="6100",
                name="Aufwendungen",
                account_type=AccountType.EXPENSE.name,
                is_active=True,
            ),
            Kontenrolle(
                mandant_id=mandate.id,
                role="SUPPLIER_PAYABLES",
                account_number="3300",
            ),
        )
    )
    session.commit()
    partner_repository = BusinessPartnerRepository(session)
    supplier = BusinessPartner(
        company_id=company.company_id,
        name="Lieferant GmbH",
        is_customer=False,
        is_supplier=True,
    )
    partner_repository.add(supplier)
    booking_repository = BookingRepository(session)
    invoice_repository = PayableInvoiceRepository(session)
    service = PayableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        invoice_repository=invoice_repository,
        chart_of_accounts_repository=ChartOfAccountsRepository(session),
    )
    return engine, session, company, supplier, service


def _post(
    service,
    company,
    supplier,
    *,
    invoice_number="ER-001",
    partner_id=None,
    **kwargs,
):
    return service.post_supplier_invoice_on_account(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner_id or supplier.partner_id,
        invoice_number=invoice_number,
        booking_date=date(2026, 3, 4),
        due_date=date(2026, 4, 3),
        items=ITEMS,
        vat_accounts=VAT,
        **kwargs,
    )


def test_success_creates_booking_invoice_and_payable_open_item_atomically():
    engine, session, company, supplier, service = _environment()
    try:
        chart_repository = ChartOfAccountsRepository(session)
        chart_repository.save_account_roles(
            company_id=company.company_id,
            account_roles=AccountingAccountRoles(
                cash_accounts=frozenset(),
                bank_accounts=frozenset(),
                general_rate_sales_accounts=frozenset(),
                supplier_payables=frozenset({"3300"}),
            ),
        )
        assert chart_repository.load_account_roles(
            company.company_id
        ).supplier_payables == frozenset({"3300"})

        invoice = _post(service, company, supplier)
        booking = session.query(Buchung).one()
        stored_invoice = session.query(Eingangsrechnung).one()
        open_item = session.query(VerbindlichkeitsOP).one()

        assert session.query(Buchung).count() == 1
        assert session.query(Eingangsrechnung).count() == 1
        assert session.query(VerbindlichkeitsOP).count() == 1
        assert booking.booking_id == str(invoice.booking_id)
        assert booking.zeilen[-1].account_number == "3300"
        assert booking.zeilen[-1].side == "CREDIT"
        assert stored_invoice.partner_id == str(supplier.partner_id)
        assert stored_invoice.invoice_number == "ER-001"
        assert stored_invoice.invoice_date == date(2026, 3, 4)
        assert stored_invoice.due_date == date(2026, 4, 3)
        assert stored_invoice.duplicate_reason is None
        assert invoice.gross_amount == Decimal("119.00")
        assert open_item.amount == Decimal("119.00")
    finally:
        session.close()
        engine.dispose()


def test_failure_after_op_staging_rolls_back_booking_and_invoice():
    engine, session, company, supplier, service = _environment()

    class FailingPayableRepository(PayableInvoiceRepository):
        def add(self, **kwargs):
            super().add(**kwargs)
            raise RuntimeError("simulierter Verbindlichkeits-OP-Fehler")

    service._invoice_repository = FailingPayableRepository(session)
    try:
        with pytest.raises(RuntimeError, match="OP-Fehler"):
            _post(service, company, supplier)
        assert session.query(Buchung).count() == 0
        assert session.query(Eingangsrechnung).count() == 0
        assert session.query(VerbindlichkeitsOP).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_mandant_and_supplier_role_are_validated():
    engine, session, company, supplier, service = _environment()
    other_company = Company(uuid4(), "Fremde UG")
    CompanyRepository(session).add(other_company)
    foreign_supplier = BusinessPartner(
        company_id=other_company.company_id,
        name="Fremdlieferant",
        is_customer=False,
        is_supplier=True,
    )
    BusinessPartnerRepository(session).add(foreign_supplier)
    try:
        with pytest.raises(ValueError, match="Lieferant gehört"):
            _post(
                service,
                company,
                supplier,
                partner_id=foreign_supplier.partner_id,
            )
        session.query(Kontenrolle).delete()
        session.commit()
        with pytest.raises(ValueError, match="genau ein"):
            _post(service, company, supplier)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("payable_type", "payable_active", "message"),
    [
        (AccountType.ASSET.name, True, "Passivkonto"),
        (AccountType.LIABILITY.name, False, "nicht vorhanden"),
    ],
)
def test_missing_or_unsuitable_payable_account_is_rejected(
    payable_type,
    payable_active,
    message,
):
    engine, session, company, supplier, service = _environment(
        payable_type=payable_type,
        payable_active=payable_active,
    )
    try:
        with pytest.raises(ValueError, match=message):
            _post(service, company, supplier)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_duplicate_supplier_invoice_requires_and_stores_reason():
    engine, session, company, supplier, service = _environment()
    try:
        _post(service, company, supplier)
        with pytest.raises(DuplicateSupplierInvoiceError):
            _post(service, company, supplier)
        assert session.query(Buchung).count() == 1
        assert session.query(Eingangsrechnung).count() == 1

        invoice = _post(
            service,
            company,
            supplier,
            duplicate_reason="Zweiter Teilbeleg desselben Lieferanten.",
        )
        stored = session.query(Eingangsrechnung).filter_by(
            invoice_id=str(invoice.invoice_id)
        ).one()
        assert stored.duplicate_reason == (
            "Zweiter Teilbeleg desselben Lieferanten."
        )
        assert session.query(Buchung).count() == 2
        assert session.query(VerbindlichkeitsOP).count() == 2
    finally:
        session.close()
        engine.dispose()


def test_wrong_or_closed_fiscal_year_is_rejected():
    engine, session, company, supplier, service = _environment()
    wrong_year = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
    try:
        with pytest.raises(ValueError, match="Geschäftsjahr"):
            service.post_supplier_invoice_on_account(
                company_id=company.company_id,
                fiscal_year=wrong_year,
                partner_id=supplier.partner_id,
                invoice_number="ER-FY",
                booking_date=date(2025, 3, 4),
                due_date=date(2025, 4, 3),
                items=ITEMS,
                vat_accounts=VAT,
            )
        session.query(Wirtschaftsjahr).update(
            {Wirtschaftsjahr.status: FiscalYearStatus.CLOSED.value}
        )
        session.commit()
        with pytest.raises(ValueError, match="abgeschlossen"):
            _post(service, company, supplier)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()
