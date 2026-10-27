"""Integrationstests für manuelle Verrechnung von Guthaben- und Rechnungs-OPs."""

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
    GuthabenOPEreignis,
    Gutschrift,
    Kontenrolle,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
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
    company = Company(uuid4(), "OP-Verrechnung UG")
    companies = CompanyRepository(session)
    companies.add(company)
    companies.add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(company_id=str(company.company_id)).one()
    session.query(Wirtschaftsjahr).one().status = FiscalYearStatus.OPEN.value
    accounts = (
        ("1000", "Bank", AccountType.ASSET),
        ("1100", "Forderungen", AccountType.ASSET),
        ("3300", "Verbindlichkeiten", AccountType.LIABILITY),
        ("2400", "Kundenguthaben", AccountType.LIABILITY),
        ("1300", "Lieferantenguthaben", AccountType.ASSET),
        ("4000", "Erlöse", AccountType.REVENUE),
        ("6100", "Aufwand", AccountType.EXPENSE),
    )
    session.add_all(
        Konto(
            mandant_id=mandate.id,
            account_number=number,
            name=name,
            account_type=account_type.name,
            is_active=True,
        )
        for number, name, account_type in accounts
    )
    roles = (
        ("BANK", "1000"),
        ("CUSTOMER_RECEIVABLES", "1100"),
        ("SUPPLIER_PAYABLES", "3300"),
        ("CUSTOMER_CREDIT_BALANCES", "2400"),
        ("SUPPLIER_CREDIT_BALANCES", "1300"),
    )
    session.add_all(
        Kontenrolle(mandant_id=mandate.id, role=role, account_number=number)
        for role, number in roles
    )
    session.commit()

    partner_repository = BusinessPartnerRepository(session)
    partner = BusinessPartner(
        company.company_id,
        "Kunde und Lieferant GmbH",
        is_customer=True,
        is_supplier=True,
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
    credit_service = CreditNotePostingService(
        booking_repository=booking_repository,
        partner_repository=partner_repository,
        credit_note_repository=CreditNoteRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    offset_repository = OpenItemOffsetRepository(session)
    offset_service = OpenItemOffsetService(
        booking_repository=booking_repository,
        offset_repository=offset_repository,
    )
    payment_service = OpenItemPaymentService(
        booking_repository=booking_repository,
        payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=chart_repository,
    )
    return (
        engine,
        session,
        company,
        partner,
        receivable_service,
        payable_service,
        credit_service,
        offset_service,
        payment_service,
    )


def _create_invoice_and_credit(
    session,
    company,
    partner,
    receivable,
    payable,
    credit_service,
    direction,
    *,
    invoice_amount=Decimal("119.00"),
    credit_amount=Decimal("119.00"),
):
    if direction is OffsetDirection.CUSTOMER:
        invoice = receivable.post_output_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            invoice_number=f"AR-{uuid4().hex[:6]}",
            booking_date=date(2026, 4, 1),
            due_date=date(2026, 5, 1),
            items=(VatBookingItem("4000", invoice_amount, 0),),
            vat_accounts=VAT,
        )
        credit_note = credit_service.post_customer_credit_note(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            note_number=f"GSC-{uuid4().hex[:6]}",
            note_date=date(2026, 4, 2),
            items=(VatBookingItem("4000", credit_amount, 0),),
            vat_accounts=VAT,
        )
        invoice_open_id = UUID(
            session.query(ForderungsOP.open_item_id)
            .filter(ForderungsOP.invoice_id == str(invoice.invoice_id))
            .scalar()
        )
    else:
        invoice = payable.post_supplier_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            invoice_number=f"AP-{uuid4().hex[:6]}",
            booking_date=date(2026, 4, 1),
            due_date=date(2026, 5, 1),
            items=(VatBookingItem("6100", invoice_amount, 0),),
            vat_accounts=VAT,
        )
        credit_note = credit_service.post_supplier_credit_note(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            note_number=f"GSS-{uuid4().hex[:6]}",
            note_date=date(2026, 4, 2),
            items=(VatBookingItem("6100", credit_amount, 0),),
            vat_accounts=VAT,
        )
        invoice_open_id = UUID(
            session.query(VerbindlichkeitsOP.open_item_id)
            .filter(VerbindlichkeitsOP.invoice_id == str(invoice.invoice_id))
            .scalar()
        )
    credit_open_id = UUID(
        session.query(GuthabenOP.open_item_id)
        .filter(GuthabenOP.credit_note_id == str(credit_note.credit_note_id))
        .scalar()
    )
    return invoice, credit_note, invoice_open_id, credit_open_id


def _post_offset(service, company, partner, direction, invoice_id, credit_id, amount):
    return service.post_offset(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        direction=direction,
        invoice_open_item_id=invoice_id,
        credit_open_item_id=credit_id,
        amount=Decimal(amount),
        settlement_date=date(2026, 4, 15),
        booking_date=date(2026, 4, 16),
    )


@pytest.mark.parametrize(
    ("direction", "invoice_account", "credit_account", "invoice_side", "credit_side"),
    [
        (OffsetDirection.CUSTOMER, "1100", "2400", EntrySide.CREDIT.value, EntrySide.DEBIT.value),
        (OffsetDirection.SUPPLIER, "3300", "1300", EntrySide.DEBIT.value, EntrySide.CREDIT.value),
    ],
)
def test_full_and_partial_offsets_reduce_both_open_items(
    direction, invoice_account, credit_account, invoice_side, credit_side
):
    environment = _environment()
    engine, session, company, partner, receivable, payable, credit_service, offsets, _ = environment
    try:
        invoice, credit_note, invoice_id, credit_id = _create_invoice_and_credit(
            session, company, partner, receivable, payable, credit_service, direction
        )
        regular_credit = offsets._offset_repository.get_credit(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            open_item_id=credit_id,
            direction=direction,
        )
        assert regular_credit.cancellation_booking_date is None
        first = _post_offset(offsets, company, partner, direction, invoice_id, credit_id, "30.00")
        first_booking = session.query(Buchung).filter_by(booking_id=str(first.booking_id)).one()
        assert {line.account_number: line.side for line in first_booking.zeilen} == {
            invoice_account: invoice_side,
            credit_account: credit_side,
        }
        assert all(line.amount == Decimal("30.00") for line in first_booking.zeilen)
        assert first_booking.booking_date == date(2026, 4, 16)
        assert first.settlement_date == date(2026, 4, 15)
        assert first.recorded_at.tzinfo is not None

        second = _post_offset(offsets, company, partner, direction, invoice_id, credit_id, "89.00")
        assert session.query(OPGuthabenverrechnung).count() == 2
        invoice_events = session.query(RechnungsOPVerrechnungsereignis).all()
        credit_events = session.query(GuthabenOPEreignis).filter(
            GuthabenOPEreignis.settlement_id.is_not(None)
        ).all()
        assert len(invoice_events) == len(credit_events) == 2
        assert {event.settlement_id for event in invoice_events} == {
            str(first.settlement_id), str(second.settlement_id)
        }
        assert {event.settlement_id for event in credit_events} == {
            str(first.settlement_id), str(second.settlement_id)
        }
        assert sum((event.amount for event in invoice_events), start=ZERO) == Decimal("119.00")
        assert sum((event.amount_delta for event in credit_events), start=ZERO) == Decimal("-119.00")
        assert session.query(Buchung).count() == 4
        assert session.query(ForderungsOP).count() + session.query(VerbindlichkeitsOP).count() == 1
        assert session.query(Gutschrift).count() == session.query(GuthabenOP).count() == 1
        if direction is OffsetDirection.CUSTOMER:
            invoice_summary = offsets.list_open_invoices(
                company_id=company.company_id,
                partner_id=partner.partner_id,
                direction=direction,
            )
            assert invoice_summary == ()
        else:
            assert offsets.list_open_invoices(
                company_id=company.company_id,
                partner_id=partner.partner_id,
                direction=direction,
            ) == ()
        assert offsets.list_open_credits(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            direction=direction,
        ) == ()
        assert CreditNoteRepository(session).get_open_amount(
            UUID(
                session.query(GuthabenOP.open_item_id)
                .filter(GuthabenOP.credit_note_id == str(credit_note.credit_note_id))
                .scalar()
            )
        ) == ZERO
        with pytest.raises(ValueError, match="Rechnungs-OP ist bereits"):
            _post_offset(
                offsets,
                company,
                partner,
                direction,
                invoice_id,
                credit_id,
                "0.01",
            )
        assert session.query(Buchung).count() == 4
        assert invoice is not None and credit_note is not None
    finally:
        session.close()
        engine.dispose()


def test_customer_payment_and_offset_share_one_consistent_invoice_balance():
    engine, session, company, partner, receivable, payable, credit_service, offsets, payments = _environment()
    try:
        _, _, invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
        )
        payment = payments.post_payment(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            open_item_id=invoice_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("20.00"),
            payment_date=date(2026, 4, 10),
            booking_date=date(2026, 4, 10),
            cash_bank_account_number="1000",
        )
        assert payment.amount == Decimal("20.00")
        assert payments.list_open_invoices(company.company_id)[0].open_amount == Decimal("99.00")
        _post_offset(
            offsets,
            company,
            partner,
            OffsetDirection.CUSTOMER,
            invoice_id,
            credit_id,
            "99.00",
        )
        assert payments.list_open_invoices(company.company_id) == ()
        assert offsets.list_open_credits(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            direction=OffsetDirection.CUSTOMER,
        )[0].available_amount == Decimal("20.00")
        assert session.query(Buchung).count() == 4
        assert session.query(Buchung).filter(
            Buchung.booking_id == str(payment.booking_id)
        ).one().zeilen[0].account_number == "1000"
    finally:
        session.close()
        engine.dispose()


def test_offset_rejects_wrong_partner_mandate_and_excess_amount():
    engine, session, company, partner, receivable, payable, credit_service, offsets, _ = _environment()
    try:
        _, _, invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
            invoice_amount=Decimal("119.00"),
            credit_amount=Decimal("200.00"),
        )
        _, _, larger_invoice_id, smaller_credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
            invoice_amount=Decimal("200.00"),
            credit_amount=Decimal("119.00"),
        )
        other_partner = BusinessPartner(company.company_id, "Anderer Kunde")
        BusinessPartnerRepository(session).add(other_partner)
        other_credit_note = credit_service.post_customer_credit_note(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=other_partner.partner_id,
            note_number=f"GSC-OTHER-{uuid4().hex[:6]}",
            note_date=date(2026, 4, 3),
            items=(VatBookingItem("4000", Decimal("119.00"), 0),),
            vat_accounts=VAT,
        )
        other_credit_id = UUID(
            session.query(GuthabenOP.open_item_id)
            .filter(GuthabenOP.credit_note_id == str(other_credit_note.credit_note_id))
            .scalar()
        )
        with pytest.raises(ValueError, match="anderen Geschäftspartner"):
            _post_offset(
                offsets,
                company,
                other_partner,
                OffsetDirection.CUSTOMER,
                invoice_id,
                credit_id,
                "10.00",
            )
        with pytest.raises(ValueError, match="anderen Geschäftspartner"):
            _post_offset(
                offsets,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                invoice_id,
                other_credit_id,
                "10.00",
            )
        other_company = Company(uuid4(), "Fremdmandant")
        CompanyRepository(session).add(other_company)
        with pytest.raises(ValueError, match="geöffneten Mandanten"):
            offsets.post_offset(
                company_id=other_company.company_id,
                fiscal_year=FY,
                partner_id=partner.partner_id,
                direction=OffsetDirection.CUSTOMER,
                invoice_open_item_id=invoice_id,
                credit_open_item_id=credit_id,
                amount=Decimal("10.00"),
                settlement_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
            )
        with pytest.raises(ValueError, match="offenen Rechnungsbetrag"):
            _post_offset(
                offsets,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                invoice_id,
                credit_id,
                "120.00",
            )
        with pytest.raises(ValueError, match="verfügbare Guthaben"):
            _post_offset(
                offsets,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                larger_invoice_id,
                smaller_credit_id,
                "120.00",
            )
        assert session.query(Buchung).count() == 5
        assert session.query(OPGuthabenverrechnung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_offset_rolls_back_booking_header_and_both_events_together():
    engine, session, company, partner, receivable, payable, credit_service, offsets, _ = _environment()
    _, _, invoice_id, credit_id = _create_invoice_and_credit(
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        OffsetDirection.CUSTOMER,
    )
    original_repository = offsets._offset_repository

    class FailingRepository(OpenItemOffsetRepository):
        def add(self, **kwargs):
            super().add(**kwargs)
            raise RuntimeError("simulierter Verrechnungsfehler")

    offsets._offset_repository = FailingRepository(session)
    try:
        with pytest.raises(RuntimeError, match="Verrechnungsfehler"):
            _post_offset(
                offsets,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                invoice_id,
                credit_id,
                "10.00",
            )
        assert session.query(Buchung).count() == 2
        assert session.query(OPGuthabenverrechnung).count() == 0
        assert session.query(RechnungsOPVerrechnungsereignis).count() == 0
        assert session.query(GuthabenOPEreignis).count() == 0
    finally:
        offsets._offset_repository = original_repository
        session.close()
        engine.dispose()
