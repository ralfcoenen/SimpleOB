"""Gezielte Integrationstests für die lesende KR-Auswertung."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.kr_monitoring_repository import KrMonitoringRepository
from simpleob.database.models import (
    Ausgangsrechnung,
    Buchung,
    Buchungszeile,
    ForderungsOP,
    Geschaeftspartner,
    GuthabenOP,
    GuthabenOPRueckerstattung,
    GuthabenOPRueckerstattungsruecknahme,
    Gutschrift,
    Konto,
    Mandant,
    RechnungsOPStorno,
    RechnungsOPZahlungsereignis,
    Wirtschaftsjahr,
    Zahlung,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking_type import BookingType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.kr_settings import (
    KrAnnualTurnoverAddition,
    KrSettings,
)
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.services.kr_monitoring_service import KrMonitoringService


def _environment():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    companies: dict[str, tuple[Company, BusinessPartner, Mandant]] = {}
    company_repository = CompanyRepository(session)
    for name in ("First UG", "Second UG"):
        company = Company(uuid4(), name)
        partner = BusinessPartner(company.company_id, f"{name} Kunde")
        company_repository.add(company)
        for year in (2024, 2025, 2026):
            company_repository.add_fiscal_year(
                company.company_id,
                FiscalYear(date(year, 1, 1), date(year, 12, 31)),
            )
        mandate = session.query(Mandant).filter_by(
            company_id=str(company.company_id)
        ).one()
        partner_id = uuid4()
        partner = BusinessPartner(
            company.company_id,
            partner.name,
            partner_id=partner_id,
        )
        session.add(
            Geschaeftspartner(
                partner_id=str(partner.partner_id),
                mandant_id=mandate.id,
                name=partner.name,
                is_customer=True,
                is_supplier=False,
                is_active=True,
            )
        )
        session.add(
            Konto(
                mandant_id=mandate.id,
                account_number="8400",
                name="Erlöse",
                account_type=AccountType.REVENUE.name,
                is_active=True,
            )
        )
        companies[name] = (company, partner, mandate)
    session.commit()

    def booking(company: Company, when: date, *, revenue=False, reversal_of=None):
        mandate = companies[company.name][2]
        fiscal_year = (
            session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.mandant_id == mandate.id,
                Wirtschaftsjahr.start_date == date(when.year, 1, 1),
            )
            .one()
        )
        model = Buchung(
            booking_id=str(uuid4()),
            wirtschaftsjahr_id=fiscal_year.id,
            booking_date=when,
            booking_type=(
                BookingType.REVERSAL.value
                if reversal_of is not None
                else BookingType.REGULAR.value
            ),
            reversal_of_booking_id=reversal_of,
        )
        if revenue:
            model.zeilen = [
                Buchungszeile(
                    position=0,
                    account_number="8400",
                    side="CREDIT",
                    amount=Decimal("100.00"),
                )
            ]
        session.add(model)
        session.flush()
        return model

    def invoice(company: Company, partner: BusinessPartner, when: date, amount: str):
        mandate = companies[company.name][2]
        source_booking = booking(company, when, revenue=True)
        invoice_id = str(uuid4())
        open_item_id = str(uuid4())
        session.add(
            Ausgangsrechnung(
                invoice_id=invoice_id,
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                invoice_number=f"R-{uuid4().hex[:8]}",
                invoice_date=when,
                due_date=when,
                gross_amount=Decimal(amount),
                booking_id=source_booking.booking_id,
            )
        )
        session.add(
            ForderungsOP(
                open_item_id=open_item_id,
                invoice_id=invoice_id,
                amount=Decimal(amount),
            )
        )
        session.flush()
        return invoice_id, open_item_id

    def payment(
        company: Company,
        partner: BusinessPartner,
        when: date,
        amount: str,
        allocations: tuple[tuple[str, str], ...],
        *,
        reversed=False,
    ):
        mandate = companies[company.name][2]
        source_booking = booking(company, when)
        payment_id = str(uuid4())
        session.add(
            Zahlung(
                payment_id=payment_id,
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                direction=PaymentDirection.CUSTOMER_RECEIPT.value,
                amount=Decimal(amount),
                payment_date=when,
                recorded_at=datetime.now(timezone.utc),
                booking_id=source_booking.booking_id,
            )
        )
        session.flush()
        for open_item_id, allocation in allocations:
            session.add(
                RechnungsOPZahlungsereignis(
                    event_id=str(uuid4()),
                    payment_id=payment_id,
                    direction=PaymentDirection.CUSTOMER_RECEIPT.value,
                    receivable_open_item_id=open_item_id,
                    payable_open_item_id=None,
                    amount=Decimal(allocation),
                    effective_date=when,
                )
            )
        session.flush()
        if reversed:
            booking(company, when, reversal_of=source_booking.booking_id)
        return payment_id

    def refund(
        company: Company,
        partner: BusinessPartner,
        when: date,
        amount: str,
        *,
        reversed=False,
        cancellation=False,
    ):
        mandate = companies[company.name][2]
        invoice_id, invoice_open_item = invoice(
            company, partner, date(2024, 6, 1), "1000.00"
        )
        if cancellation:
            cancellation_booking = booking(company, date(2025, 12, 31))
            transfer_booking = booking(company, date(2025, 12, 31))
            cancellation_id = str(uuid4())
            session.add(
                RechnungsOPStorno(
                    storno_id=cancellation_id,
                    mandant_id=mandate.id,
                    partner_id=str(partner.partner_id),
                    receivable_invoice_id=invoice_id,
                    payable_invoice_id=None,
                    receivable_open_item_id=invoice_open_item,
                    payable_open_item_id=None,
                    booking_id=cancellation_booking.booking_id,
                    credit_booking_id=transfer_booking.booking_id,
                    amount=Decimal("1000.00"),
                    closed_open_amount=ZERO,
                    recorded_at=datetime.now(timezone.utc),
                    reason="Teststorno",
                )
            )
            session.flush()
            credit_open_item = GuthabenOP(
                open_item_id=str(uuid4()),
                credit_note_id=None,
                invoice_cancellation_id=cancellation_id,
                amount=Decimal("1000.00"),
            )
        else:
            note_booking = booking(company, date(2025, 12, 31))
            note_id = str(uuid4())
            session.add(
                Gutschrift(
                    credit_note_id=note_id,
                    mandant_id=mandate.id,
                    partner_id=str(partner.partner_id),
                    credit_note_kind="CUSTOMER",
                    note_number=f"G-{uuid4().hex[:8]}",
                    note_date=date(2025, 12, 31),
                    original_receivable_invoice_id=invoice_id,
                    original_payable_invoice_id=None,
                    booking_id=note_booking.booking_id,
                    duplicate_reason=None,
                )
            )
            session.flush()
            credit_open_item = GuthabenOP(
                open_item_id=str(uuid4()),
                credit_note_id=note_id,
                invoice_cancellation_id=None,
                amount=Decimal("1000.00"),
            )
        session.add(credit_open_item)
        refund_booking = booking(company, when)
        refund_id = str(uuid4())
        session.add(
            GuthabenOPRueckerstattung(
                refund_id=refund_id,
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                open_item_id=credit_open_item.open_item_id,
                direction="CUSTOMER",
                amount=Decimal(amount),
                refund_date=when,
                booking_id=refund_booking.booking_id,
                recorded_at=datetime.now(timezone.utc),
            )
        )
        session.flush()
        if reversed:
            reversal_booking = booking(
                company,
                when,
                reversal_of=refund_booking.booking_id,
            )
            session.add(
                GuthabenOPRueckerstattungsruecknahme(
                    reversal_id=str(uuid4()),
                    refund_id=refund_id,
                    reversal_booking_id=reversal_booking.booking_id,
                    recorded_at=datetime.now(timezone.utc),
                    reason="Test-Rücknahme",
                )
            )
        return refund_id

    return engine, session, companies, booking, invoice, payment, refund


def test_kr_totals_use_calendar_dates_allocations_refunds_and_reversals():
    engine, session, companies, _booking, invoice, payment, refund = _environment()
    try:
        company, partner, _mandate = companies["First UG"]
        prior_invoice = invoice(company, partner, date(2024, 3, 1), "700.00")
        second_invoice = invoice(company, partner, date(2025, 4, 1), "500.00")
        payment(
            company,
            partner,
            date(2025, 12, 31),
            "1200.00",
            ((prior_invoice[1], "700.00"), (second_invoice[1], "300.00")),
        )
        reversed_invoice = invoice(company, partner, date(2024, 5, 1), "400.00")
        payment(
            company,
            partner,
            date(2025, 12, 31),
            "400.00",
            ((reversed_invoice[1], "400.00"),),
            reversed=True,
        )
        current_invoice_1 = invoice(company, partner, date(2025, 12, 1), "500.00")
        current_invoice_2 = invoice(company, partner, date(2025, 12, 2), "500.00")
        payment(
            company,
            partner,
            date(2026, 1, 1),
            "1000.00",
            ((current_invoice_1[1], "500.00"), (current_invoice_2[1], "500.00")),
        )
        refund(company, partner, date(2026, 1, 1), "100.00")
        refund(
            company,
            partner,
            date(2026, 2, 1),
            "200.00",
            cancellation=True,
        )
        refund(
            company,
            partner,
            date(2026, 3, 1),
            "90.00",
            reversed=True,
        )

        second_company, second_partner, _second_mandate = companies["Second UG"]
        other_invoice = invoice(second_company, second_partner, date(2025, 8, 1), "999.00")
        payment(
            second_company,
            second_partner,
            date(2026, 1, 1),
            "999.00",
            ((other_invoice[1], "999.00"),),
        )
        session.commit()

        repository = KrMonitoringRepository(session)
        previous = repository.get_calendar_year_totals(
            company_id=company.company_id,
            calendar_year=2025,
        )
        current = repository.get_calendar_year_totals(
            company_id=company.company_id,
            calendar_year=2026,
        )
        assert previous.customer_payments == Decimal("1000.00")
        assert previous.customer_refunds == ZERO
        assert current.customer_payments == Decimal("1000.00")
        assert current.customer_refunds == Decimal("300.00")
        assert current.balance == Decimal("700.00")
        assert current.has_direct_revenue_bookings is False
    finally:
        session.close()
        engine.dispose()


def test_kr_service_uses_current_calendar_year_and_direct_revenue_warning():
    engine, session, companies, booking, invoice, _payment, _refund = _environment()
    try:
        company, partner, _mandate = companies["First UG"]
        invoice(company, partner, date(2025, 12, 1), "100.00")
        booking(company, date(2026, 5, 1), revenue=True)
        session.commit()
        service = KrMonitoringService(
            KrMonitoringRepository(session),
            CompanyRepository(session),
        )

        summary = service.get_summary(
            company_id=company.company_id,
            today=date(2026, 7, 1),
        )
        assert summary.previous_year.calendar_year == 2025
        assert summary.current_year.calendar_year == 2026
        assert summary.current_year.has_direct_revenue_bookings is True
        assert summary.previous_year.has_direct_revenue_bookings is False
        assert summary.previous_year.limit is None
        assert summary.current_year.limit is None
        assert summary.activity_start_date is None

        service.save_settings(
            KrSettings(
                company_id=company.company_id,
                activity_start_date=date(2026, 3, 1),
                external_turnovers=(
                    KrAnnualTurnoverAddition(2025, Decimal("500.00")),
                    KrAnnualTurnoverAddition(2026, Decimal("750.25")),
                ),
            )
        )
        summary = service.get_summary(
            company_id=company.company_id,
            today=date(2026, 7, 1),
        )
        assert summary.previous_year.external_turnover == Decimal("500.00")
        assert summary.previous_year.limit is None
        assert summary.current_year.external_turnover == Decimal("750.25")
        assert summary.current_year.balance == Decimal("750.25")
        assert summary.current_year.limit == Decimal("25000.00")

        service.save_settings(
            KrSettings(
                company_id=company.company_id,
                activity_start_date=date(2026, 3, 1),
            )
        )
        later_summary = service.get_summary(
            company_id=company.company_id,
            today=date(2027, 1, 1),
        )
        assert later_summary.current_year.limit == Decimal("100000.00")
        assert later_summary.previous_year.limit == Decimal("25000.00")
    finally:
        session.close()
        engine.dispose()


def test_unpaid_output_invoice_does_not_increase_kr_turnover():
    engine, session, companies, _booking, invoice, _payment, _refund = _environment()
    try:
        company, partner, _mandate = companies["First UG"]
        invoice(company, partner, date(2026, 5, 1), "1250.00")
        session.commit()

        totals = KrMonitoringRepository(session).get_calendar_year_totals(
            company_id=company.company_id,
            calendar_year=2026,
        )

        assert totals.customer_payments == ZERO
        assert totals.customer_refunds == ZERO
        assert totals.balance == ZERO
    finally:
        session.close()
        engine.dispose()
