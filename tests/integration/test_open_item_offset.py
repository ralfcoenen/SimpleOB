"""Integrationstests für manuelle Verrechnung von Guthaben- und Rechnungs-OPs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Barrier
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
from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import (
    Buchung,
    ForderungsOP,
    GuthabenOP,
    GuthabenOPEreignis,
    GuthabenOPRueckerstattung,
    Gutschrift,
    Kontenrolle,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
)
from simpleob.database.open_item_credit_refund_repository import (
    OpenItemCreditRefundRepository,
)
from simpleob.database.open_item_invoice_cancellation_repository import (
    OpenItemInvoiceCancellationRepository,
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
from simpleob.services.open_item_credit_refund_service import (
    OpenItemCreditRefundService,
)
from simpleob.services.open_item_invoice_cancellation_service import (
    OpenItemInvoiceCancellationService,
)
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


def _environment(database_url="sqlite:///:memory:"):
    engine = create_engine(database_url)

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
        ("1010", "Kasse", AccountType.ASSET),
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
        ("CASH", "1010"),
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


def _refund_service(session):
    booking_repository = BookingRepository(session)
    offset_repository = OpenItemOffsetRepository(session)
    refund_repository = OpenItemCreditRefundRepository(
        session,
        offset_repository=offset_repository,
    )
    return OpenItemCreditRefundService(
        booking_repository=booking_repository,
        refund_repository=refund_repository,
        offset_repository=offset_repository,
        chart_of_accounts_repository=ChartOfAccountsRepository(session),
    )


def _post_refund(
    service,
    company,
    partner,
    direction,
    credit_id,
    amount,
    *,
    account="1000",
    booking_date=date(2026, 4, 16),
    refund_date=date(2026, 4, 15),
):
    return service.post_refund(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        open_item_id=credit_id,
        direction=direction,
        amount=Decimal(amount),
        refund_date=refund_date,
        booking_date=booking_date,
        cash_bank_account_number=account,
    )


def _create_storno_credit(
    session,
    company,
    partner,
    receivable,
    payable,
    direction,
):
    booking_repository = BookingRepository(session)
    if direction is OffsetDirection.CUSTOMER:
        invoice = receivable.post_output_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            invoice_number=f"AR-STORNO-{uuid4().hex[:6]}",
            booking_date=date(2026, 4, 1),
            due_date=date(2026, 5, 1),
            items=(VatBookingItem("4000", Decimal("119.00"), 0),),
            vat_accounts=VAT,
        )
        open_item_id = UUID(session.query(ForderungsOP.open_item_id).filter_by(
            invoice_id=str(invoice.invoice_id)
        ).scalar())
        payment_direction = PaymentDirection.CUSTOMER_RECEIPT
    else:
        invoice = payable.post_supplier_invoice_on_account(
            company_id=company.company_id,
            fiscal_year=FY,
            partner_id=partner.partner_id,
            invoice_number=f"AP-STORNO-{uuid4().hex[:6]}",
            booking_date=date(2026, 4, 1),
            due_date=date(2026, 5, 1),
            items=(VatBookingItem("6100", Decimal("119.00"), 0),),
            vat_accounts=VAT,
        )
        open_item_id = UUID(session.query(VerbindlichkeitsOP.open_item_id).filter_by(
            invoice_id=str(invoice.invoice_id)
        ).scalar())
        payment_direction = PaymentDirection.SUPPLIER_PAYMENT
    payment_service = OpenItemPaymentService(
        booking_repository=booking_repository,
        payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=ChartOfAccountsRepository(session),
    )
    payment_service.post_payment(
        company_id=company.company_id,
        fiscal_year=FY,
        partner_id=partner.partner_id,
        open_item_id=open_item_id,
        direction=payment_direction,
        amount=Decimal("20.00"),
        payment_date=date(2026, 4, 2),
        booking_date=date(2026, 4, 2),
        cash_bank_account_number="1000",
    )
    cancellation_service = OpenItemInvoiceCancellationService(
        OpenItemInvoiceCancellationRepository(
            session=session,
            booking_repository=booking_repository,
        )
    )
    storno_id = cancellation_service.cancel_invoice(
        company_id=company.company_id,
        fiscal_year=FY,
        open_item_id=open_item_id,
        booking_date=date(2026, 4, 3),
        reason="Testguthaben erzeugen",
        confirmed=True,
    )
    credit_id = UUID(session.query(GuthabenOP.open_item_id).filter_by(
        invoice_cancellation_id=str(storno_id)
    ).scalar())
    return credit_id


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
    ("direction", "account", "control_account", "control_side", "cash_side"),
    [
        (OffsetDirection.CUSTOMER, "1000", "2400", EntrySide.DEBIT, EntrySide.CREDIT),
        (OffsetDirection.CUSTOMER, "1010", "2400", EntrySide.DEBIT, EntrySide.CREDIT),
        (OffsetDirection.SUPPLIER, "1000", "1300", EntrySide.CREDIT, EntrySide.DEBIT),
        (OffsetDirection.SUPPLIER, "1010", "1300", EntrySide.CREDIT, EntrySide.DEBIT),
    ],
)
def test_credit_refunds_use_origin_control_account_and_configured_bank_or_cash(
    direction, account, control_account, control_side, cash_side
):
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        offsets,
        _payments,
    ) = _environment()
    try:
        _invoice, _credit_note, _invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            direction,
        )
        refund = _post_refund(
            _refund_service(session),
            company,
            partner,
            direction,
            credit_id,
            "119.00",
            account=account,
        )
        booking = session.query(Buchung).filter_by(
            booking_id=str(refund.booking_id)
        ).one()
        lines = {line.account_number: line for line in booking.zeilen}
        assert lines[control_account].side == control_side.value
        assert lines[account].side == cash_side.value
        assert lines[control_account].amount == lines[account].amount == Decimal("119.00")
        assert refund.refund_date == date(2026, 4, 15)
        assert session.query(GuthabenOPRueckerstattung).count() == 1
        assert session.query(GuthabenOPEreignis).count() == 0
        assert offsets._offset_repository.get_credit(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            open_item_id=credit_id,
            direction=direction,
        ).available_amount == ZERO
        assert CreditNoteRepository(session).get_open_amount(credit_id) == ZERO
    finally:
        session.close()
        engine.dispose()


def test_credit_refund_partial_repeated_and_full_reduces_credit_once():
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        offsets,
        _payments,
    ) = _environment()
    try:
        _invoice, _note, _invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
        )
        service = _refund_service(session)
        _post_refund(service, company, partner, OffsetDirection.CUSTOMER, credit_id, "30.00")
        assert offsets._offset_repository.get_credit(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            open_item_id=credit_id,
            direction=OffsetDirection.CUSTOMER,
        ).available_amount == Decimal("89.00")
        _post_refund(service, company, partner, OffsetDirection.CUSTOMER, credit_id, "40.00")
        assert CreditNoteRepository(session).get_open_amount(credit_id) == Decimal("49.00")
        _post_refund(service, company, partner, OffsetDirection.CUSTOMER, credit_id, "49.00")
        assert CreditNoteRepository(session).get_open_amount(credit_id) == ZERO
        assert session.query(GuthabenOPRueckerstattung).count() == 3
        assert session.query(GuthabenOPEreignis).count() == 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("direction", [OffsetDirection.CUSTOMER, OffsetDirection.SUPPLIER])
def test_storno_based_credit_refund_uses_credit_transfer_date(direction):
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        _credit_service,
        offsets,
        _payments,
    ) = _environment()
    try:
        credit_id = _create_storno_credit(
            session, company, partner, receivable, payable, direction
        )
        service = _refund_service(session)
        before_booking_count = session.query(Buchung).count()
        with pytest.raises(ValueError, match="nicht vor dem Entstehungsdatum"):
            _post_refund(
                service,
                company,
                partner,
                direction,
                credit_id,
                "1.00",
                booking_date=date(2026, 4, 2),
            )
        assert session.query(Buchung).count() == before_booking_count
        assert session.query(GuthabenOPRueckerstattung).count() == 0
        _post_refund(
            service,
            company,
            partner,
            direction,
            credit_id,
            "20.00",
            booking_date=date(2026, 4, 3),
        )
        assert offsets._offset_repository.get_credit(
            company_id=company.company_id,
            partner_id=partner.partner_id,
            open_item_id=credit_id,
            direction=direction,
        ).available_amount == ZERO
    finally:
        session.close()
        engine.dispose()


def test_credit_refund_rejects_overrefund_and_rolls_back_partial_booking(monkeypatch):
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        _offsets,
        _payments,
    ) = _environment()
    try:
        _invoice, _note, _invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
        )
        service = _refund_service(session)
        before = session.query(Buchung).count()
        with pytest.raises(ValueError, match="übersteigt das verfügbare Guthaben"):
            _post_refund(
                service,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                credit_id,
                "119.01",
            )
        assert session.query(Buchung).count() == before
        assert session.query(GuthabenOPRueckerstattung).count() == 0

        def fail_add(**_kwargs):
            raise RuntimeError("Nebenbuchfehler")

        monkeypatch.setattr(service._refund_repository, "add", fail_add)
        with pytest.raises(RuntimeError, match="Nebenbuchfehler"):
            _post_refund(
                service,
                company,
                partner,
                OffsetDirection.CUSTOMER,
                credit_id,
                "10.00",
            )
        assert session.query(Buchung).count() == before
        assert session.query(GuthabenOPRueckerstattung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_regular_credit_refund_cannot_precede_credit_booking_date():
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        _offsets,
        _payments,
    ) = _environment()
    try:
        _invoice, _note, _invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
        )
        before = session.query(Buchung).count()
        with pytest.raises(ValueError, match="nicht vor dem Entstehungsdatum"):
            _post_refund(
                _refund_service(session),
                company,
                partner,
                OffsetDirection.CUSTOMER,
                credit_id,
                "1.00",
                booking_date=date(2026, 4, 1),
            )
        assert session.query(Buchung).count() == before
        assert session.query(GuthabenOPRueckerstattung).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_sqlite_concurrent_offset_and_credit_refund_cannot_overconsume(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'credit-consumption-race.db'}"
    (
        engine,
        session,
        company,
        partner,
        receivable,
        payable,
        credit_service,
        _offsets,
        _payments,
    ) = _environment(database_url)
    invoice_id = credit_id = None
    try:
        _invoice, _note, invoice_id, credit_id = _create_invoice_and_credit(
            session,
            company,
            partner,
            receivable,
            payable,
            credit_service,
            OffsetDirection.CUSTOMER,
        )
    finally:
        session.close()

    start = Barrier(2)

    def consume(kind):
        worker_session = Session(engine)
        try:
            worker_offsets_repo = OpenItemOffsetRepository(worker_session)
            booking_repository = BookingRepository(worker_session)
            start.wait(timeout=5)
            if kind == "offset":
                service = OpenItemOffsetService(
                    booking_repository=booking_repository,
                    offset_repository=worker_offsets_repo,
                )
                return _post_offset(
                    service,
                    company,
                    partner,
                    OffsetDirection.CUSTOMER,
                    invoice_id,
                    credit_id,
                    "80.00",
                )
            return _post_refund(
                OpenItemCreditRefundService(
                    booking_repository=booking_repository,
                    refund_repository=OpenItemCreditRefundRepository(
                        worker_session,
                        offset_repository=worker_offsets_repo,
                    ),
                    offset_repository=worker_offsets_repo,
                    chart_of_accounts_repository=ChartOfAccountsRepository(
                        worker_session
                    ),
                ),
                company,
                partner,
                OffsetDirection.CUSTOMER,
                credit_id,
                "80.00",
            )
        finally:
            worker_session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(consume, kind) for kind in ("offset", "refund")]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(("success", future.result(timeout=10)))
                except Exception as exc:
                    outcomes.append(("failure", exc))
        assert [outcome[0] for outcome in outcomes].count("success") == 1
        assert [outcome[0] for outcome in outcomes].count("failure") == 1
        failure = next(outcome[1] for outcome in outcomes if outcome[0] == "failure")
        assert isinstance(failure, (ValueError, DatabaseLockError))

        check_session = Session(engine)
        try:
            remaining = CreditNoteRepository(check_session).get_open_amount(credit_id)
            assert remaining == Decimal("39.00")
            assert check_session.query(OPGuthabenverrechnung).count() + check_session.query(
                GuthabenOPRueckerstattung
            ).count() == 1
        finally:
            check_session.close()
    finally:
        engine.dispose()


def test_sqlite_credit_reservation_does_not_nest_in_physical_transaction():
    engine, session, *_rest = _environment()
    try:
        connection = session.connection()
        connection.exec_driver_sql("BEGIN")
        with pytest.raises(DatabaseLockError, match="bereits eine Datenbanktransaktion"):
            OpenItemOffsetRepository(session).reserve_credit_mutation()
    finally:
        session.rollback()
        session.close()
        engine.dispose()


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
