"""Integrationstests für atomare Ausgangsrechnungen auf Ziel."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from simpleob.core.config import ApplicationConfig
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base, Database
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    ForderungsOP,
    Kontenrolle,
    Konto,
    Mandant,
    Wirtschaftsjahr,
)
from simpleob.database.receivable_invoice_repository import ReceivableInvoiceRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.receivable_invoice import ReceivableInvoice, ReceivableOpenItem
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")
ITEMS = (VatBookingItem("8400", Decimal("119.00"), 19),)


def test_database_enables_sqlite_foreign_key_enforcement():
    database = Database(
        ApplicationConfig(
            data_dir=Path("/tmp"),
            database_file=Path("/tmp/unused.sqlite"),
            taxonomy_dir=Path("/tmp/taxonomy"),
            config_file=Path("/tmp/config.toml"),
            database_url_override="sqlite:///:memory:",
        )
    )
    try:
        with database.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        database.dispose()


def _environment(*, receivable_type: str = "ASSET", active: bool = True):
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "Test UG")
    CompanyRepository(session).add(company)
    CompanyRepository(session).add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(company_id=str(company.company_id)).one()
    fiscal_year_model = session.query(Wirtschaftsjahr).one()
    fiscal_year_model.status = FiscalYearStatus.OPEN.value
    session.add_all(
        [
            Konto(
                mandant_id=mandate.id,
                account_number="1200",
                name="Forderungen",
                account_type=receivable_type,
                is_active=active,
            ),
            Konto(
                mandant_id=mandate.id,
                account_number="8400",
                name="Umsatzerlöse",
                account_type=AccountType.REVENUE.name,
                is_active=True,
            ),
            Kontenrolle(
                mandant_id=mandate.id,
                role="CUSTOMER_RECEIVABLES",
                account_number="1200",
            ),
        ]
    )
    session.commit()
    partner_repo = BusinessPartnerRepository(session)
    partner = BusinessPartner(company.company_id, "Kunde GmbH")
    partner_repo.add(partner)
    bookings = BookingRepository(session)
    invoices = ReceivableInvoiceRepository(session)
    service = ReceivableInvoicePostingService(
        booking_repository=bookings,
        partner_repository=partner_repo,
        invoice_repository=invoices,
        chart_of_accounts_repository=ChartOfAccountsRepository(session),
    )
    return engine, session, company, partner, service


def _post(service, company, partner, *, invoice_number="AR-1", **kwargs):
    return service.post_output_invoice_on_account(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        invoice_number=invoice_number,
        booking_date=date(2026, 4, 3),
        due_date=date(2026, 5, 3),
        items=ITEMS,
        vat_accounts=VAT,
        **kwargs,
    )


def test_success_creates_one_booking_invoice_and_open_item_atomically():
    engine, session, company, partner, service = _environment()
    try:
        invoice = _post(service, company, partner)
        assert session.query(Buchung).count() == 1
        assert session.query(Ausgangsrechnung).count() == 1
        assert session.query(ForderungsOP).count() == 1
        booking = session.query(Buchung).one()
        assert booking.booking_id == str(invoice.booking_id)
        assert booking.zeilen[0].account_number == "1200"
        assert invoice.gross_amount == Decimal("119.00")
        assert session.query(ForderungsOP).one().amount == Decimal("119.00")
    finally:
        session.close()
        engine.dispose()


def test_failure_after_op_staging_rolls_back_all_records():
    engine, session, company, partner, service = _environment()

    class FailingInvoiceRepository(ReceivableInvoiceRepository):
        def add(self, **kwargs):
            super().add(**kwargs)
            raise RuntimeError("simulierter OP-Fehler")

    service._invoice_repository = FailingInvoiceRepository(session)
    try:
        with pytest.raises(RuntimeError, match="simulierter"):
            _post(service, company, partner)
        assert session.query(Buchung).count() == 0
        assert session.query(Ausgangsrechnung).count() == 0
        assert session.query(ForderungsOP).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_duplicate_invoice_number_and_id_are_rejected():
    engine, session, company, partner, service = _environment()
    try:
        invoice = _post(service, company, partner)
        with pytest.raises(ValueError, match="Rechnungsnummer"):
            _post(service, company, partner)
        with pytest.raises(ValueError, match="Rechnungs-ID"):
            _post(
                service,
                company,
                partner,
                invoice_number="AR-2",
                invoice_id=invoice.invoice_id,
            )
        assert session.query(Buchung).count() == 1
        assert session.query(ForderungsOP).count() == 1
        open_item_id = session.query(ForderungsOP.open_item_id).scalar()
        with pytest.raises(ValueError, match="OP-ID"):
            _post(
                service,
                company,
                partner,
                invoice_number="AR-3",
                open_item_id=UUID(open_item_id),
            )
        assert session.query(Buchung).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_duplicate_booking_origin_is_rejected():
    engine, session, company, partner, service = _environment()
    try:
        invoice = _post(service, company, partner)
        second_invoice = ReceivableInvoice(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            invoice_number="AR-2",
            invoice_date=date(2026, 4, 4),
            due_date=date(2026, 5, 4),
            gross_amount=Decimal("119.00"),
            booking_id=invoice.booking_id,
        )
        with pytest.raises(ValueError, match="Hauptbuchbuchung"):
            service._invoice_repository.add(
                invoice=second_invoice,
                open_item=ReceivableOpenItem(
                    invoice_id=second_invoice.invoice_id,
                    amount=second_invoice.gross_amount,
                ),
                fiscal_year=FY,
                commit=False,
            )
        assert session.query(Buchung).count() == 1
        assert session.query(Ausgangsrechnung).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_sqlite_composite_foreign_key_prevents_cross_tenant_partner_reference():
    engine, session, company, partner, service = _environment()
    other_company = Company(uuid4(), "Andere UG")
    CompanyRepository(session).add(other_company)
    other_mandate = session.query(Mandant).filter_by(
        company_id=str(other_company.company_id)
    ).one()
    CompanyRepository(session).add_fiscal_year(other_company.company_id, FY)
    other_booking = Booking(
        booking_date=date(2026, 4, 3),
        lines=(
            BookingLine("1200", EntrySide.DEBIT, Decimal("1.00")),
            BookingLine("8400", EntrySide.CREDIT, Decimal("1.00")),
        ),
    )
    BookingRepository(session).add(
        company_id=other_company.company_id,
        fiscal_year=FY,
        booking=other_booking,
    )
    try:
        _post(service, company, partner)
        session.add(
            Ausgangsrechnung(
                invoice_id=str(uuid4()),
                mandant_id=other_mandate.id,
                partner_id=str(partner.partner_id),
                invoice_number="FREMDE-AR",
                invoice_date=date(2026, 4, 3),
                due_date=date(2026, 5, 3),
                gross_amount=Decimal("119.00"),
                booking_id=str(other_booking.booking_id),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        assert session.query(Ausgangsrechnung).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_foreign_partner_and_fiscal_year_are_rejected():
    engine, session, company, partner, service = _environment()
    other_company = Company(uuid4(), "Andere UG")
    CompanyRepository(session).add(other_company)
    other_partner = BusinessPartner(other_company.company_id, "Fremdkunde")
    BusinessPartnerRepository(session).add(other_partner)
    try:
        with pytest.raises(ValueError, match="Kunde gehört"):
            service.post_output_invoice_on_account(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=other_partner.partner_id,
                invoice_number="AR-X",
                booking_date=date(2026, 4, 3),
                due_date=date(2026, 5, 3),
                items=ITEMS,
                vat_accounts=VAT,
            )
        wrong_fy = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
        with pytest.raises(ValueError, match="Geschäftsjahr"):
            service.post_output_invoice_on_account(
                company_id=company.company_id,
                fiscal_year=wrong_fy,
                partner_id=partner.partner_id,
                invoice_number="AR-Y",
                booking_date=date(2025, 4, 3),
                due_date=date(2025, 5, 3),
                items=ITEMS,
                vat_accounts=VAT,
            )
        session.query(Wirtschaftsjahr).filter_by(mandant_id=1).update(
            {Wirtschaftsjahr.status: FiscalYearStatus.CLOSED.value}
        )
        session.commit()
        with pytest.raises(ValueError, match="abgeschlossen"):
            _post(service, company, partner, invoice_number="AR-Z")
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("receivable_type", "active", "message"),
    [("LIABILITY", True, "Aktivkonto"), ("ASSET", False, "nicht vorhanden")],
)
def test_unsuitable_receivables_account_rejected(receivable_type, active, message):
    engine, session, company, partner, service = _environment(
        receivable_type=receivable_type, active=active
    )
    try:
        with pytest.raises(ValueError, match=message):
            _post(service, company, partner)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_missing_receivables_role_is_rejected():
    engine, session, company, partner, service = _environment()
    session.query(Kontenrolle).delete()
    session.commit()
    try:
        with pytest.raises(ValueError, match="genau ein"):
            _post(service, company, partner)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_configured_but_missing_receivables_account_is_rejected():
    engine, session, company, partner, service = _environment()
    session.query(Konto).filter_by(account_number="1200").delete()
    session.commit()
    try:
        with pytest.raises(ValueError, match="nicht vorhanden"):
            _post(service, company, partner)
        assert session.query(Buchung).count() == 0
    finally:
        session.close()
        engine.dispose()
