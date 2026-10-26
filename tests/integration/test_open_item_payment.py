"""Integrationstests für Zahlungen auf Rechnungs-OPs."""

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
from simpleob.database.database import Base
from simpleob.database.models import (
    Buchung,
    Buchungszeile,
    ForderungsOP,
    Kontenrolle,
    Konto,
    Mandant,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
)
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.database.payable_invoice_repository import PayableInvoiceRepository
from simpleob.database.receivable_invoice_repository import ReceivableInvoiceRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.money import ZERO
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.open_item_payment_service import OpenItemPaymentService
from simpleob.services.payable_invoice_posting_service import (
    PayableInvoicePostingService,
)
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")


def _environment():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "Zahlungstest UG")
    company_repository = CompanyRepository(session)
    company_repository.add(company)
    company_repository.add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(company_id=str(company.company_id)).one()
    fiscal_year = session.query(Wirtschaftsjahr).one()
    fiscal_year.status = FiscalYearStatus.OPEN.value
    account_data = (
        ("1200", "Forderungen", AccountType.ASSET),
        ("3300", "Verbindlichkeiten", AccountType.LIABILITY),
        ("1000", "Kasse", AccountType.ASSET),
        ("8400", "Erlöse", AccountType.REVENUE),
        ("6100", "Aufwand", AccountType.EXPENSE),
        ("1576", "Vorsteuer", AccountType.ASSET),
        ("1776", "Umsatzsteuer", AccountType.LIABILITY),
        ("1570", "Vorsteuer reduziert", AccountType.ASSET),
        ("1770", "Umsatzsteuer reduziert", AccountType.LIABILITY),
    )
    session.add_all(
        Konto(
            mandant_id=mandate.id,
            account_number=number,
            name=name,
            account_type=account_type.name,
            is_active=True,
        )
        for number, name, account_type in account_data
    )
    session.add_all(
        (
            Kontenrolle(mandant_id=mandate.id, role="CUSTOMER_RECEIVABLES", account_number="1200"),
            Kontenrolle(mandant_id=mandate.id, role="SUPPLIER_PAYABLES", account_number="3300"),
            Kontenrolle(mandant_id=mandate.id, role="CASH", account_number="1000"),
        )
    )
    session.commit()

    partner_repository = BusinessPartnerRepository(session)
    partner = BusinessPartner(
        company.company_id, "Partner GmbH", is_customer=True, is_supplier=True
    )
    partner_repository.add(partner)
    booking_repository = BookingRepository(session)
    chart_repository = ChartOfAccountsRepository(session)
    receivable_service = ReceivableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        invoice_repository=ReceivableInvoiceRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    payable_service = PayableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        invoice_repository=PayableInvoiceRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    payment_service = OpenItemPaymentService(
        booking_repository=booking_repository,
        payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    return engine, session, company, partner, receivable_service, payable_service, payment_service


def _create_receivable(service, company, partner, number="AR-1"):
    return service.post_output_invoice_on_account(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        invoice_number=number,
        booking_date=date(2026, 4, 1),
        due_date=date(2026, 5, 1),
        items=(VatBookingItem("8400", Decimal("119.00"), 0),),
        vat_accounts=VAT,
    )


def _create_payable(service, company, partner, number="AP-1"):
    return service.post_supplier_invoice_on_account(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        invoice_number=number,
        booking_date=date(2026, 4, 1),
        due_date=date(2026, 5, 1),
        items=(VatBookingItem("6100", Decimal("119.00"), 0),),
        vat_accounts=VAT,
    )


def _open_item_id(session, invoice):
    model = (
        ForderungsOP
        if session.query(ForderungsOP).filter_by(invoice_id=str(invoice.invoice_id)).one_or_none()
        else VerbindlichkeitsOP
    )
    return UUID(
        session.query(model.open_item_id)
        .filter_by(invoice_id=str(invoice.invoice_id))
        .scalar()
    )


def _pay(session, service, company, partner, invoice, direction, amount):
    return service.post_payment(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        open_item_id=_open_item_id(session, invoice),
        direction=direction,
        amount=Decimal(amount),
        payment_date=date(2026, 4, 15),
        booking_date=date(2026, 4, 16),
        cash_bank_account_number="1000",
    )


def _pay_allocations(
    service, company, partner, direction, amount, allocations
):
    return service.post_payment_allocations(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        direction=direction,
        amount=Decimal(amount),
        allocations=tuple(
            (open_item_id, Decimal(allocation))
            for open_item_id, allocation in allocations
        ),
        payment_date=date(2026, 4, 15),
        booking_date=date(2026, 4, 16),
        cash_bank_account_number="1000",
    )


def test_full_customer_receipt_posts_one_booking_and_closes_receivable():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        invoice = _create_receivable(receivable, company, partner)
        payment = _pay(session, payments, company, partner, invoice, PaymentDirection.CUSTOMER_RECEIPT, "119.00")
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 1
        assert session.query(RechnungsOPZahlungsereignis).count() == 1
        booking = session.query(Buchung).filter_by(booking_id=str(payment.booking_id)).one()
        assert booking.description == "Kundenzahlung Partner GmbH, Rechnung AR-1"
        lines = {line.account_number: line for line in booking.zeilen}
        assert (lines["1000"].side, lines["1000"].amount) == (EntrySide.DEBIT.value, Decimal("119.00"))
        assert (lines["1200"].side, lines["1200"].amount) == (EntrySide.CREDIT.value, Decimal("119.00"))
        assert session.query(ForderungsOP).one().amount - session.query(RechnungsOPZahlungsereignis.amount).scalar() == ZERO
        stored_payment = session.query(Zahlung).one()
        assert stored_payment.payment_date == date(2026, 4, 15)
        assert booking.booking_date == date(2026, 4, 16)
        assert stored_payment.recorded_at is not None
        with pytest.raises(ValueError, match="vollständig ausgeglichen"):
            _pay(
                session,
                payments,
                company,
                partner,
                invoice,
                PaymentDirection.CUSTOMER_RECEIPT,
                "0.01",
            )
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_full_supplier_payment_uses_payable_debit_and_bank_credit():
    engine, session, company, partner, _, payable, payments = _environment()
    try:
        invoice = _create_payable(payable, company, partner)
        payment = _pay(session, payments, company, partner, invoice, PaymentDirection.SUPPLIER_PAYMENT, "119.00")
        booking = session.query(Buchung).filter_by(booking_id=str(payment.booking_id)).one()
        assert booking.description == "Lieferantenzahlung Partner GmbH, Rechnung AP-1"
        lines = {line.account_number: line for line in booking.zeilen}
        assert (lines["3300"].side, lines["3300"].amount) == (EntrySide.DEBIT.value, Decimal("119.00"))
        assert (lines["1000"].side, lines["1000"].amount) == (EntrySide.CREDIT.value, Decimal("119.00"))
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 1
        assert session.query(VerbindlichkeitsOP).one().amount == session.query(RechnungsOPZahlungsereignis.amount).scalar()
    finally:
        session.close()
        engine.dispose()


def test_several_partial_payments_calculate_remaining_open_amount():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        invoice = _create_receivable(receivable, company, partner)
        first_payment = _pay(
            session,
            payments,
            company,
            partner,
            invoice,
            PaymentDirection.CUSTOMER_RECEIPT,
            "30.00",
        )
        first_booking = session.query(Buchung).filter_by(
            booking_id=str(first_payment.booking_id)
        ).one()
        assert first_booking.description == "Teilzahlung Partner GmbH, Rechnung AR-1"
        assert payments.list_open_invoices(company.company_id)[0].open_amount == Decimal("89.00")
        second_payment = _pay(
            session,
            payments,
            company,
            partner,
            invoice,
            PaymentDirection.CUSTOMER_RECEIPT,
            "40.00",
        )
        second_booking = session.query(Buchung).filter_by(
            booking_id=str(second_payment.booking_id)
        ).one()
        assert second_booking.description == "Teilzahlung Partner GmbH, Rechnung AR-1"
        summary = payments.list_open_invoices(company.company_id)[0]
        assert summary.open_amount == Decimal("49.00")
        assert session.query(Zahlung).count() == 2
        assert session.query(RechnungsOPZahlungsereignis).count() == 2
        assert session.query(Buchung).count() == 3
    finally:
        session.close()
        engine.dispose()


def test_partial_supplier_payment_has_a_readable_booking_description():
    engine, session, company, partner, _, payable, payments = _environment()
    try:
        invoice = _create_payable(payable, company, partner)
        payment = _pay(
            session,
            payments,
            company,
            partner,
            invoice,
            PaymentDirection.SUPPLIER_PAYMENT,
            "30.00",
        )
        booking = session.query(Buchung).filter_by(
            booking_id=str(payment.booking_id)
        ).one()
        assert booking.description == "Teilzahlung an Partner GmbH, Rechnung AP-1"
    finally:
        session.close()
        engine.dispose()


def test_customer_collection_allocates_one_payment_to_multiple_invoices():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        first_invoice = _create_receivable(receivable, company, partner, "AR-1")
        second_invoice = _create_receivable(receivable, company, partner, "AR-2")
        first_open_item = _open_item_id(session, first_invoice)
        second_open_item = _open_item_id(session, second_invoice)

        payment = _pay_allocations(
            payments,
            company,
            partner,
            PaymentDirection.CUSTOMER_RECEIPT,
            "149.00",
            ((first_open_item, "119.00"), (second_open_item, "30.00")),
        )

        events = session.query(RechnungsOPZahlungsereignis).all()
        booking = session.query(Buchung).filter_by(
            booking_id=str(payment.booking_id)
        ).one()
        assert booking.description == "Kundenzahlung Partner GmbH, 2 Rechnungen"
        control_lines = [line for line in booking.zeilen if line.account_number == "1200"]
        cash_lines = [line for line in booking.zeilen if line.account_number == "1000"]
        assert session.query(Buchung).count() == 3
        assert session.query(Zahlung).count() == 1
        assert len(events) == 2
        assert {event.payment_id for event in events} == {str(payment.payment_id)}
        assert {event.receivable_open_item_id for event in events} == {
            str(first_open_item),
            str(second_open_item),
        }
        assert len(control_lines) == 2
        assert all(line.side == EntrySide.CREDIT.value for line in control_lines)
        assert sum((line.amount for line in control_lines), start=ZERO) == payment.amount
        assert len(cash_lines) == 1
        assert cash_lines[0].side == EntrySide.DEBIT.value
        assert cash_lines[0].amount == payment.amount
        assert payments._payment_repository.get_open_invoice(
            company_id=company.company_id,
            open_item_id=first_open_item,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
        ).open_amount == ZERO
        assert payments._payment_repository.get_open_invoice(
            company_id=company.company_id,
            open_item_id=second_open_item,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
        ).open_amount == Decimal("89.00")
    finally:
        session.close()
        engine.dispose()


def test_supplier_payment_allocates_one_payment_to_multiple_invoices():
    engine, session, company, partner, _, payable, payments = _environment()
    try:
        first_invoice = _create_payable(payable, company, partner, "AP-1")
        second_invoice = _create_payable(payable, company, partner, "AP-2")
        first_open_item = _open_item_id(session, first_invoice)
        second_open_item = _open_item_id(session, second_invoice)

        payment = _pay_allocations(
            payments,
            company,
            partner,
            PaymentDirection.SUPPLIER_PAYMENT,
            "149.00",
            ((first_open_item, "119.00"), (second_open_item, "30.00")),
        )

        events = session.query(RechnungsOPZahlungsereignis).all()
        booking = session.query(Buchung).filter_by(
            booking_id=str(payment.booking_id)
        ).one()
        assert booking.description == "Lieferantenzahlung Partner GmbH, 2 Rechnungen"
        control_lines = [line for line in booking.zeilen if line.account_number == "3300"]
        cash_lines = [line for line in booking.zeilen if line.account_number == "1000"]
        assert session.query(Buchung).count() == 3
        assert session.query(Zahlung).count() == 1
        assert len(events) == 2
        assert {event.payment_id for event in events} == {str(payment.payment_id)}
        assert {event.payable_open_item_id for event in events} == {
            str(first_open_item),
            str(second_open_item),
        }
        assert len(control_lines) == 2
        assert all(line.side == EntrySide.DEBIT.value for line in control_lines)
        assert sum((line.amount for line in control_lines), start=ZERO) == payment.amount
        assert len(cash_lines) == 1
        assert cash_lines[0].side == EntrySide.CREDIT.value
        assert cash_lines[0].amount == payment.amount
        assert payments._payment_repository.get_open_invoice(
            company_id=company.company_id,
            open_item_id=first_open_item,
            direction=PaymentDirection.SUPPLIER_PAYMENT,
        ).open_amount == ZERO
        assert payments._payment_repository.get_open_invoice(
            company_id=company.company_id,
            open_item_id=second_open_item,
            direction=PaymentDirection.SUPPLIER_PAYMENT,
        ).open_amount == Decimal("89.00")
    finally:
        session.close()
        engine.dispose()


def test_invalid_payment_allocations_are_rejected_before_booking():
    engine, session, company, partner, receivable, _, payments = _environment()
    other_partner = BusinessPartner(company.company_id, "Andere Kundin")
    BusinessPartnerRepository(session).add(other_partner)
    try:
        invoice = _create_receivable(receivable, company, partner, "AR-1")
        other_invoice = _create_receivable(
            receivable, company, other_partner, "AR-2"
        )
        open_item_id = _open_item_id(session, invoice)
        other_open_item_id = _open_item_id(session, other_invoice)
        other_company = Company(uuid4(), "Anderer Mandant")
        CompanyRepository(session).add(other_company)

        with pytest.raises(ValueError, match="exakt dem Zahlungsbetrag"):
            _pay_allocations(
                payments,
                company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "100.00",
                ((open_item_id, "99.99"),),
            )
        with pytest.raises(ValueError, match="nur einmal"):
            _pay_allocations(
                payments,
                company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "100.00",
                ((open_item_id, "50.00"), (open_item_id, "50.00")),
            )
        with pytest.raises(ValueError, match="demselben Geschäftspartner"):
            _pay_allocations(
                payments,
                company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "20.00",
                ((open_item_id, "10.00"), (other_open_item_id, "10.00")),
            )
        with pytest.raises(ValueError, match="geöffneten Mandanten"):
            _pay_allocations(
                payments,
                other_company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "10.00",
                ((open_item_id, "10.00"),),
            )
        with pytest.raises(ValueError, match="Zuordnung übersteigt"):
            _pay_allocations(
                payments,
                company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "120.00",
                ((open_item_id, "120.00"),),
            )
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 0
        assert session.query(RechnungsOPZahlungsereignis).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_overpayment_is_rejected_without_new_records():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        invoice = _create_receivable(receivable, company, partner)
        _pay(session, payments, company, partner, invoice, PaymentDirection.CUSTOMER_RECEIPT, "100.00")
        with pytest.raises(ValueError, match="übersteigt"):
            _pay(session, payments, company, partner, invoice, PaymentDirection.CUSTOMER_RECEIPT, "20.00")
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 1
        assert session.query(RechnungsOPZahlungsereignis).count() == 1
        assert payments.list_open_invoices(company.company_id)[0].open_amount == Decimal("19.00")
    finally:
        session.close()
        engine.dispose()


def test_failure_after_payment_staging_rolls_back_booking_and_payment():
    engine, session, company, partner, receivable, _, payments = _environment()
    first_invoice = _create_receivable(receivable, company, partner, "AR-1")
    second_invoice = _create_receivable(receivable, company, partner, "AR-2")
    original_repository = payments._payment_repository

    class FailingRepository(OpenItemPaymentRepository):
        def add(self, **kwargs):
            super().add(**kwargs)
            raise RuntimeError("simulierter Zuordnungsfehler")

    payments._payment_repository = FailingRepository(session)
    try:
        with pytest.raises(RuntimeError, match="Zuordnungsfehler"):
            _pay_allocations(
                payments,
                company,
                partner,
                PaymentDirection.CUSTOMER_RECEIPT,
                "10.00",
                (
                    (_open_item_id(session, first_invoice), "5.00"),
                    (_open_item_id(session, second_invoice), "5.00"),
                ),
            )
        assert session.query(Buchung).count() == 2
        assert session.query(Zahlung).count() == 0
        assert session.query(RechnungsOPZahlungsereignis).count() == 0
    finally:
        payments._payment_repository = original_repository
        session.close()
        engine.dispose()


def test_partner_and_fiscal_year_validation_preserve_existing_records():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        invoice = _create_receivable(receivable, company, partner)
        with pytest.raises(ValueError, match="demselben Geschäftspartner"):
            payments.post_payment(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=uuid4(),
                open_item_id=_open_item_id(session, invoice),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount=Decimal("10.00"),
                payment_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
                cash_bank_account_number="1000",
            )
        other_company = Company(uuid4(), "Fremdmandant")
        CompanyRepository(session).add(other_company)
        with pytest.raises(ValueError, match="geöffneten Mandanten"):
            payments.post_payment(
                company_id=other_company.company_id,
                fiscal_year=FY,
                partner_id=partner.partner_id,
                open_item_id=_open_item_id(session, invoice),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount=Decimal("10.00"),
                payment_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
                cash_bank_account_number="1000",
            )
        with pytest.raises(ValueError, match="außerhalb"):
            payments.post_payment(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=partner.partner_id,
                open_item_id=_open_item_id(session, invoice),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount=Decimal("10.00"),
                payment_date=date(2026, 4, 15),
                booking_date=date(2027, 1, 1),
                cash_bank_account_number="1000",
            )
        year_model = session.query(Wirtschaftsjahr).one()
        year_model.status = FiscalYearStatus.CLOSED.value
        session.commit()
        with pytest.raises(ValueError, match="abgeschlossen"):
            payments.post_payment(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=partner.partner_id,
                open_item_id=_open_item_id(session, invoice),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount=Decimal("10.00"),
                payment_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
                cash_bank_account_number="1000",
            )
        assert session.query(Buchung).count() == 1
        assert session.query(Zahlung).count() == 0
        assert session.query(Buchungszeile).count() == 2
    finally:
        session.close()
        engine.dispose()


def test_wrong_cash_bank_role_and_nonpositive_amount_are_rejected():
    engine, session, company, partner, receivable, _, payments = _environment()
    try:
        invoice = _create_receivable(receivable, company, partner)
        with pytest.raises(ValueError, match="Bank- oder Kassenkonto"):
            payments.post_payment(
                company_id=company.company_id,
                fiscal_year=FY,
                partner_id=partner.partner_id,
                open_item_id=_open_item_id(session, invoice),
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount=Decimal("10.00"),
                payment_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
                cash_bank_account_number="8400",
            )
        with pytest.raises(ValueError, match="größer als 0"):
            _pay(session, payments, company, partner, invoice, PaymentDirection.CUSTOMER_RECEIPT, "0.00")
        assert session.query(Buchung).count() == 1
    finally:
        session.close()
        engine.dispose()
