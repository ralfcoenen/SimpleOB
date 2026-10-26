"""Focused integration coverage for manual payment allocation corrections."""

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
    Buchung,
    ForderungsOP,
    GuthabenOP,
    Kontenrolle,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.database.payable_invoice_repository import PayableInvoiceRepository
from simpleob.database.payment_allocation_correction_repository import (
    PaymentAllocationCorrectionRepository,
)
from simpleob.database.receivable_invoice_repository import ReceivableInvoiceRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.credit_note_posting_service import CreditNotePostingService
from simpleob.services.open_item_offset_service import OpenItemOffsetService
from simpleob.services.open_item_payment_service import OpenItemPaymentService
from simpleob.services.payable_invoice_posting_service import (
    PayableInvoicePostingService,
)
from simpleob.services.payment_allocation_correction_service import (
    PaymentAllocationCorrectionService,
)
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")


def _env():
    engine = create_engine("sqlite:///:memory:")
    @event.listens_for(engine, "connect")
    def fk(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "Correction test")
    companies = CompanyRepository(session)
    companies.add(company)
    companies.add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(company_id=str(company.company_id)).one()
    session.query(Wirtschaftsjahr).one().status = FiscalYearStatus.OPEN.value
    session.add_all(Konto(mandant_id=mandate.id, account_number=n, name=n,
        account_type=t.name, is_active=True) for n, t in (("1200", AccountType.ASSET),
        ("1210", AccountType.ASSET), ("1000", AccountType.ASSET), ("8400", AccountType.REVENUE),
        ("3300", AccountType.LIABILITY), ("3301", AccountType.LIABILITY), ("2400", AccountType.LIABILITY),
        ("6100", AccountType.EXPENSE),
        ("1576", AccountType.ASSET), ("1570", AccountType.ASSET),
        ("1776", AccountType.LIABILITY), ("1770", AccountType.LIABILITY)))
    session.add_all((Kontenrolle(mandant_id=mandate.id, role="CUSTOMER_RECEIVABLES", account_number="1200"),
                     Kontenrolle(mandant_id=mandate.id, role="SUPPLIER_PAYABLES", account_number="3300"),
                     Kontenrolle(mandant_id=mandate.id, role="CUSTOMER_CREDIT_BALANCES", account_number="2400"),
                     Kontenrolle(mandant_id=mandate.id, role="CASH", account_number="1000")))
    session.commit()
    partners = BusinessPartnerRepository(session)
    partner = BusinessPartner(company.company_id, "Customer and supplier", is_customer=True, is_supplier=True)
    partners.add(partner)
    booking = BookingRepository(session)
    chart = ChartOfAccountsRepository(session)
    receivables = ReceivableInvoicePostingService(booking_repository=booking,
        partner_repository=partners, invoice_repository=ReceivableInvoiceRepository(session),
        chart_of_accounts_repository=chart)
    payables = PayableInvoicePostingService(booking_repository=booking,
        partner_repository=partners, invoice_repository=PayableInvoiceRepository(session),
        chart_of_accounts_repository=chart)
    payments = OpenItemPaymentService(booking_repository=booking,
        payment_repository=OpenItemPaymentRepository(session), chart_of_accounts_repository=chart)
    credits = CreditNotePostingService(booking_repository=booking, partner_repository=partners,
        credit_note_repository=CreditNoteRepository(session), chart_of_accounts_repository=chart)
    offsets = OpenItemOffsetService(booking_repository=booking,
        offset_repository=OpenItemOffsetRepository(session))
    corrections = PaymentAllocationCorrectionService(booking_repository=booking,
        correction_repository=PaymentAllocationCorrectionRepository(session),
        offset_repository=OpenItemOffsetRepository(session), payment_repository=OpenItemPaymentRepository(session))
    return engine, session, company, partner, receivables, payables, payments, corrections, credits, offsets


def _invoice(service, company, partner, number):
    return service.post_output_invoice_on_account(company_id=company.company_id, fiscal_year=FY,
        partner_id=partner.partner_id, invoice_number=number, booking_date=date(2026, 4, 1),
        due_date=date(2026, 5, 1), items=(VatBookingItem("8400", Decimal("119.00"), 0),), vat_accounts=VAT)


def _supplier_invoice(service, company, partner, number):
    return service.post_supplier_invoice_on_account(company_id=company.company_id, fiscal_year=FY,
        partner_id=partner.partner_id, invoice_number=number, booking_date=date(2026, 4, 1),
        due_date=date(2026, 5, 1), items=(VatBookingItem("6100", Decimal("119.00"), 0),), vat_accounts=VAT)


def _op(session, invoice):
    return UUID(session.query(ForderungsOP.open_item_id).filter_by(invoice_id=str(invoice.invoice_id)).scalar())


def _payable_op(session, invoice):
    return UUID(session.query(VerbindlichkeitsOP.open_item_id).filter_by(invoice_id=str(invoice.invoice_id)).scalar())


def _correctable_id(session, payment):
    return UUID(session.query(RechnungsOPZahlungsereignis.event_id).filter_by(payment_id=str(payment.payment_id)).scalar())


def test_partial_and_repeated_correction_preserve_payment_and_recalculate_balances():
    engine, session, company, partner, invoices, _payables, payments, corrections, _credits, _offsets = _env()
    try:
        source = _invoice(invoices, company, partner, "AR-S")
        target = _invoice(invoices, company, partner, "AR-T")
        payment = payments.post_payment(company_id=company.company_id, fiscal_year=FY, partner_id=partner.partner_id,
            open_item_id=_op(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("100.00"), payment_date=date(2026, 4, 5), booking_date=date(2026, 4, 6),
            cash_bank_account_number="1000")
        event_id = _correctable_id(session, payment)
        original_booking_count = session.query(Buchung).count()
        corrections.correct(company_id=company.company_id, fiscal_year=FY, original_event_id=event_id,
            target_open_item_id=_op(session, target), amount=Decimal("30.00"), correction_date=date(2026, 4, 7),
            booking_date=date(2026, 4, 7), reason="Teilbetrag falsch zugeordnet", confirmed=True)
        corrections.correct(company_id=company.company_id, fiscal_year=FY, original_event_id=event_id,
            target_open_item_id=_op(session, target), amount=Decimal("20.00"), correction_date=date(2026, 4, 8),
            booking_date=date(2026, 4, 8), reason="Weiterer Teilbetrag", confirmed=True)
        invoices_now = {item.open_item_id: item.open_amount for item in payments.list_open_invoices(company.company_id)}
        assert invoices_now[_op(session, source)] == Decimal("69.00")
        assert invoices_now[_op(session, target)] == Decimal("69.00")
        assert session.query(Zahlung).one().payment_id == str(payment.payment_id)
        assert session.query(Buchung).count() == original_booking_count
        assert session.query(RechnungsOPZahlungsereignis).one().amount == Decimal("100.00")
        assert session.query(Zahlungszuordnungskorrekturereignis).count() == 4
        with pytest.raises(ValueError, match="korrigierbaren"):
            corrections.correct(company_id=company.company_id, fiscal_year=FY, original_event_id=event_id,
                target_open_item_id=_op(session, target), amount=Decimal("51.00"),
                correction_date=date(2026, 4, 9), booking_date=date(2026, 4, 9),
                reason="Über Restbetrag", confirmed=True)
        assert session.query(Zahlungszuordnungskorrektur).count() == 2
    finally:
        session.close()
        engine.dispose()


def test_different_control_accounts_create_only_control_reclassification():
    engine, session, company, partner, invoices, _payables, payments, corrections, _credits, _offsets = _env()
    try:
        source = _invoice(invoices, company, partner, "AR-S")
        payment = payments.post_payment(company_id=company.company_id, fiscal_year=FY, partner_id=partner.partner_id,
            open_item_id=_op(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("50.00"), payment_date=date(2026, 4, 5), booking_date=date(2026, 4, 6),
            cash_bank_account_number="1000")
        role = session.query(Kontenrolle).filter_by(role="CUSTOMER_RECEIVABLES").one()
        role.account_number = "1210"
        session.commit()
        target = _invoice(invoices, company, partner, "AR-T")
        before = session.query(Buchung).count()
        corrections.correct(company_id=company.company_id, fiscal_year=FY, original_event_id=_correctable_id(session, payment),
            target_open_item_id=_op(session, target), amount=Decimal("50.00"), correction_date=date(2026, 4, 7),
            booking_date=date(2026, 4, 7), reason="Sachkonto korrigieren", confirmed=True)
        assert session.query(Buchung).count() == before + 1
        correction = session.query(Zahlungszuordnungskorrektur).one()
        booking = session.query(Buchung).filter_by(booking_id=correction.booking_id).one()
        lines = booking.zeilen
        assert {(line.account_number, line.side, line.amount) for line in lines} == {
            ("1200", EntrySide.DEBIT.value, Decimal("50.00")),
            ("1210", EntrySide.CREDIT.value, Decimal("50.00")),
        }
        assert "1000" not in {line.account_number for line in lines}
    finally:
        session.close()
        engine.dispose()


def test_reason_confirmation_target_and_transaction_rollback_are_enforced():
    engine, session, company, partner, invoices, _payables, payments, corrections, _credits, _offsets = _env()
    try:
        source = _invoice(invoices, company, partner, "AR-S")
        payment = payments.post_payment(company_id=company.company_id, fiscal_year=FY, partner_id=partner.partner_id,
            open_item_id=_op(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("60.00"), payment_date=date(2026, 4, 5), booking_date=date(2026, 4, 6),
            cash_bank_account_number="1000")
        role = session.query(Kontenrolle).filter_by(role="CUSTOMER_RECEIVABLES").one()
        role.account_number = "1210"
        session.commit()
        target = _invoice(invoices, company, partner, "AR-T")
        args = dict(company_id=company.company_id, fiscal_year=FY, original_event_id=_correctable_id(session, payment),
            target_open_item_id=_op(session, target), amount=Decimal("10.00"), correction_date=date(2026, 4, 7),
            booking_date=date(2026, 4, 7))
        with pytest.raises(ValueError, match="Begründung"):
            corrections.correct(**args, reason="  ", confirmed=True)
        with pytest.raises(ValueError, match="bestätigt"):
            corrections.correct(**args, reason="Begründet", confirmed=False)
        assert session.query(Zahlungszuordnungskorrektur).count() == 0
        before = session.query(Buchung).count()
        invalid_date_args = {**args, "correction_date": date(2027, 1, 1)}
        with pytest.raises(ValueError, match="Korrekturdatum"):
            corrections.correct(**invalid_date_args, reason="Fehler erzwingen", confirmed=True)
        assert session.query(Buchung).count() == before
        assert session.query(Zahlungszuordnungskorrektur).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_supplier_payment_allocation_can_be_corrected_with_payable_direction():
    engine, session, company, partner, _receivables, payables, payments, corrections, _credits, _offsets = _env()
    try:
        source = _supplier_invoice(payables, company, partner, "AP-S")
        target = _supplier_invoice(payables, company, partner, "AP-T")
        payment = payments.post_payment(company_id=company.company_id, fiscal_year=FY, partner_id=partner.partner_id,
            open_item_id=_payable_op(session, source), direction=PaymentDirection.SUPPLIER_PAYMENT,
            amount=Decimal("50.00"), payment_date=date(2026, 4, 5), booking_date=date(2026, 4, 6),
            cash_bank_account_number="1000")
        corrections.correct(company_id=company.company_id, fiscal_year=FY,
            original_event_id=_correctable_id(session, payment), target_open_item_id=_payable_op(session, target),
            amount=Decimal("50.00"), correction_date=date(2026, 4, 7), booking_date=date(2026, 4, 7),
            reason="Lieferantenzuordnung korrigieren", confirmed=True)
        balances = {item.open_item_id: item.open_amount for item in payments.list_open_invoices(company.company_id)}
        assert balances[_payable_op(session, source)] == Decimal("119.00")
        assert balances[_payable_op(session, target)] == Decimal("69.00")
        correction = session.query(Zahlungszuordnungskorrektur).one()
        assert correction.direction == PaymentDirection.SUPPLIER_PAYMENT.value
        assert correction.booking_id is None
        assert session.query(Zahlung).one().payment_id == str(payment.payment_id)
    finally:
        session.close()
        engine.dispose()


def test_payment_correction_preserves_partial_customer_credit_offset():
    engine, session, company, partner, receivables, _payables, payments, corrections, credits, offsets = _env()
    try:
        source = _invoice(receivables, company, partner, "AR-OFFSET-SOURCE")
        target = _invoice(receivables, company, partner, "AR-OFFSET-TARGET")
        payment = payments.post_payment(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            open_item_id=_op(session, source),
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("50.00"),
            payment_date=date(2026, 4, 5),
            booking_date=date(2026, 4, 6),
            cash_bank_account_number="1000",
        )
        note = credits.post_customer_credit_note(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            note_number="CN-OFFSET-1",
            note_date=date(2026, 4, 7),
            items=(VatBookingItem("8400", Decimal("30.00"), 0),),
            vat_accounts=VAT,
        )
        credit_id = UUID(
            session.query(GuthabenOP.open_item_id)
            .filter_by(credit_note_id=str(note.credit_note_id))
            .scalar()
        )
        offset = offsets.post_offset(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            direction=OffsetDirection.CUSTOMER,
            invoice_open_item_id=_op(session, source),
            credit_open_item_id=credit_id,
            amount=Decimal("20.00"),
            settlement_date=date(2026, 4, 8),
            booking_date=date(2026, 4, 8),
        )
        booking_count_before = session.query(Buchung).count()
        cash_lines_before = sum(
            1 for booking in session.query(Buchung).all()
            for line in booking.zeilen if line.account_number == "1000"
        )

        corrections.correct(
            company_id=company.company_id,
            fiscal_year=FY,
            original_event_id=_correctable_id(session, payment),
            target_open_item_id=_op(session, target),
            amount=Decimal("20.00"),
            correction_date=date(2026, 4, 9),
            booking_date=date(2026, 4, 9),
            reason="Teilzahlung der zweiten Rechnung zuordnen",
            confirmed=True,
        )

        balances = {
            invoice.open_item_id: invoice.open_amount
            for invoice in payments.list_open_invoices(company.company_id)
        }
        assert balances[_op(session, source)] == Decimal("69.00")
        assert balances[_op(session, target)] == Decimal("99.00")
        stored_offset = session.query(OPGuthabenverrechnung).one()
        assert stored_offset.settlement_id == str(offset.settlement_id)
        assert stored_offset.amount == Decimal("20.00")
        assert session.query(RechnungsOPVerrechnungsereignis).one().settlement_id == str(offset.settlement_id)
        assert session.query(Buchung).count() == booking_count_before
        cash_lines_after = sum(
            1 for booking in session.query(Buchung).all()
            for line in booking.zeilen if line.account_number == "1000"
        )
        assert cash_lines_after == cash_lines_before == 1
    finally:
        session.close()
        engine.dispose()
