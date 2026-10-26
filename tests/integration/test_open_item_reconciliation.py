"""Integrationstests für historische OP-Sammelkonto-Abstimmungen."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from simpleob.accounting.financial_statement_builder import FinancialStatementBuilder
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.credit_note_repository import CreditNoteRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Buchung,
    Buchungszeile,
    ForderungsOP,
    GuthabenOP,
    Kontenrolle,
    Konto,
    Mandant,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.database.open_item_reconciliation_repository import (
    OpenItemReconciliationRepository,
    _correction_balance_adjustment,
)
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
from simpleob.domain.journal import Journal
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.hgb.balance_sheet_structure import create_hgb_balance_sheet_structure
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.csv_chart_of_accounts_importer import CsvChartOfAccountsImporter
from simpleob.services.closing_accounts import ClosingAccounts
from simpleob.services.closing_service import ClosingService
from simpleob.services.credit_note_posting_service import CreditNotePostingService
from simpleob.services.fiscal_year_closing_workflow import FiscalYearClosingWorkflow
from simpleob.services.fiscal_year_opening_workflow import FiscalYearOpeningWorkflow
from simpleob.services.fiscal_year_transfer_service import FiscalYearTransferService
from simpleob.services.open_item_offset_service import OpenItemOffsetService
from simpleob.services.open_item_payment_service import OpenItemPaymentService
from simpleob.services.payable_invoice_posting_service import (
    PayableInvoicePostingService,
)
from simpleob.services.payment_allocation_correction_service import (
    PaymentAllocationCorrectionService,
)
from simpleob.services.posting_service import PostingService
from simpleob.services.receivable_invoice_posting_service import (
    ReceivableInvoicePostingService,
)

FY25 = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
FY26 = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")


def _environment():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "OP-Abstimmung UG")
    company_repository = CompanyRepository(session)
    company_repository.add(company)
    company_repository.add_fiscal_year(company.company_id, FY25)
    company_repository.add_fiscal_year(company.company_id, FY26)
    mandate = session.query(Mandant).filter_by(company_id=str(company.company_id)).one()
    session.query(Wirtschaftsjahr).update({Wirtschaftsjahr.status: FiscalYearStatus.OPEN.value})
    accounts = (
        ("1000", "Bank", AccountType.ASSET),
        ("1200", "Forderungen", AccountType.ASSET),
        ("1210", "Weitere Forderungen", AccountType.ASSET),
        ("3300", "Verbindlichkeiten", AccountType.LIABILITY),
        ("2400", "Kundenguthaben", AccountType.LIABILITY),
        ("1300", "Lieferantenguthaben", AccountType.ASSET),
        ("8400", "Erlöse", AccountType.REVENUE),
        ("6100", "Aufwand", AccountType.EXPENSE),
        ("1576", "Vorsteuer", AccountType.ASSET),
        ("1570", "Vorsteuer ermäßigt", AccountType.ASSET),
        ("1776", "Umsatzsteuer", AccountType.LIABILITY),
        ("1770", "Umsatzsteuer ermäßigt", AccountType.LIABILITY),
    )
    session.add_all(Konto(mandant_id=mandate.id, account_number=number, name=name,
                          account_type=kind.name, is_active=True)
                   for number, name, kind in accounts)
    session.add_all(Kontenrolle(mandant_id=mandate.id, role=role, account_number=number)
                   for role, number in (
                       ("BANK", "1000"), ("CUSTOMER_RECEIVABLES", "1200"),
                       ("SUPPLIER_PAYABLES", "3300"),
                       ("CUSTOMER_CREDIT_BALANCES", "2400"),
                       ("SUPPLIER_CREDIT_BALANCES", "1300"),
                   ))
    session.commit()
    partners = BusinessPartnerRepository(session)
    partner = BusinessPartner(company.company_id, "Kunde GmbH", is_customer=True, is_supplier=True)
    partners.add(partner)
    bookings = BookingRepository(session)
    chart = ChartOfAccountsRepository(session)
    receivables = ReceivableInvoicePostingService(
        booking_repository=bookings, partner_repository=partners,
        invoice_repository=ReceivableInvoiceRepository(session),
        chart_of_accounts_repository=chart,
    )
    payables = PayableInvoicePostingService(
        booking_repository=bookings,
        partner_repository=partners,
        invoice_repository=PayableInvoiceRepository(session),
        chart_of_accounts_repository=chart,
    )
    payments = OpenItemPaymentService(
        booking_repository=bookings, payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=chart,
    )
    credits = CreditNotePostingService(
        booking_repository=bookings, partner_repository=partners,
        credit_note_repository=CreditNoteRepository(session),
        chart_of_accounts_repository=chart,
    )
    offsets = OpenItemOffsetService(
        booking_repository=bookings,
        offset_repository=OpenItemOffsetRepository(session),
    )
    corrections = PaymentAllocationCorrectionService(
        booking_repository=bookings,
        correction_repository=PaymentAllocationCorrectionRepository(session),
        offset_repository=OpenItemOffsetRepository(session),
        payment_repository=OpenItemPaymentRepository(session),
    )
    return (
        engine, session, company, partner, receivables, payables, payments,
        credits, offsets, corrections,
    )


def _invoice(service, company, partner, year=FY26, booking_date=date(2026, 4, 1), number="AR-1"):
    return service.post_output_invoice_on_account(
        company_id=company.company_id, fiscal_year=year, partner_id=partner.partner_id,
        invoice_number=number, booking_date=booking_date, due_date=date(booking_date.year, 12, 31),
        items=(VatBookingItem("8400", Decimal("119.00"), 0),), vat_accounts=VAT,
    )


def _supplier_invoice(service, company, partner, number="AP-1"):
    return service.post_supplier_invoice_on_account(
        company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
        invoice_number=number, booking_date=date(2026, 4, 1), due_date=date(2026, 12, 31),
        items=(VatBookingItem("6100", Decimal("119.00"), 0),), vat_accounts=VAT,
    )


def _open_id(session, invoice):
    return UUID(session.query(ForderungsOP.open_item_id)
                .filter_by(invoice_id=str(invoice.invoice_id)).scalar())


def test_reconciles_unpaid_invoice_and_historical_partial_payment_cutoff():
    engine, session, company, partner, invoices, _payables, payments, _credits, _offsets, _corrections = _environment()
    try:
        invoice = _invoice(invoices, company, partner)
        op_id = _open_id(session, invoice)
        before = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 10)
        )
        assert before.rows[0].ledger_balance == Decimal("119.00")
        assert before.rows[0].open_item_balance == Decimal("119.00")
        payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=op_id, direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("50.00"), payment_date=date(2026, 4, 12),
            booking_date=date(2026, 4, 15), cash_bank_account_number="1000",
        )
        historical = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 14)
        )
        after = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 15)
        )
        assert historical.rows[0].open_item_balance == Decimal("119.00")
        assert after.rows[0].ledger_balance == Decimal("69.00")
        assert after.rows[0].open_item_balance == Decimal("69.00")
        assert after.rows[0].difference == Decimal("0.00")
    finally:
        session.close()
        engine.dispose()


def test_unlinked_manual_control_account_movement_is_reported_without_mutation():
    engine, session, company, partner, invoices, _payables, _payments, _credits, _offsets, _corrections = _environment()
    try:
        _invoice(invoices, company, partner)
        before_counts = (session.query(Buchung).count(), session.query(ForderungsOP).count())
        booking = Buchung(
            booking_id=str(uuid4()), wirtschaftsjahr_id=session.query(Wirtschaftsjahr).filter_by(
                start_date=FY26.start_date
            ).one().id,
            booking_date=date(2026, 4, 3), voucher_no="MAN-1", description="Manuelle Forderungsbuchung",
        )
        session.add(booking)
        session.flush()
        session.add_all((
            Buchungszeile(buchung_id=booking.id, position=1, account_number="1200",
                          side=EntrySide.DEBIT.value, amount=Decimal("10.00")),
            Buchungszeile(buchung_id=booking.id, position=2, account_number="8400",
                          side=EntrySide.CREDIT.value, amount=Decimal("10.00")),
        ))
        session.commit()
        report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 3)
        )
        receivable = report.rows[0]
        assert receivable.difference == Decimal("10.00")
        assert receivable.status == "UNGEKLAERTE_BEWEGUNG"
        assert len(receivable.unexplained_movements) == 1
        assert (session.query(Buchung).count(), session.query(ForderungsOP).count()) == (
            before_counts[0] + 1, before_counts[1]
        )
        assert session.query(RechnungsOPZahlungsereignis).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_partial_payment_and_credit_offset_reconcile_both_customer_roles():
    engine, session, company, partner, invoices, _payables, payments, credits, offsets, _corrections = _environment()
    try:
        invoice = _invoice(invoices, company, partner)
        note = credits.post_customer_credit_note(
            company_id=company.company_id, fiscal_year=FY26,
            partner_id=partner.partner_id, note_number="CN-1",
            note_date=date(2026, 4, 2),
            items=(VatBookingItem("8400", Decimal("30.00"), 0),), vat_accounts=VAT,
        )
        invoice_id = _open_id(session, invoice)
        credit_id = UUID(session.query(GuthabenOP.open_item_id)
                         .filter_by(credit_note_id=str(note.credit_note_id)).scalar())
        payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=invoice_id, direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("20.00"), payment_date=date(2026, 4, 10),
            booking_date=date(2026, 4, 10), cash_bank_account_number="1000",
        )
        offsets.post_offset(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            direction=OffsetDirection.CUSTOMER, invoice_open_item_id=invoice_id,
            credit_open_item_id=credit_id, amount=Decimal("30.00"),
            settlement_date=date(2026, 4, 11), booking_date=date(2026, 4, 11),
        )
        report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 11)
        )
        by_role = {row.role: row for row in report.rows}
        assert by_role["CUSTOMER_RECEIVABLES"].ledger_balance == Decimal("69.00")
        assert by_role["CUSTOMER_RECEIVABLES"].open_item_balance == Decimal("69.00")
        assert by_role["CUSTOMER_CREDIT_BALANCES"].ledger_balance == Decimal("0.00")
        assert by_role["CUSTOMER_CREDIT_BALANCES"].open_item_balance == Decimal("0.00")
    finally:
        session.close()
        engine.dispose()


def test_supplier_invoice_and_credit_offset_reconcile_both_supplier_roles():
    engine, session, company, partner, _receivables, payables, _payments, credits, offsets, _corrections = _environment()
    try:
        invoice = _supplier_invoice(payables, company, partner)
        note = credits.post_supplier_credit_note(
            company_id=company.company_id, fiscal_year=FY26,
            partner_id=partner.partner_id, note_number="SUP-CN-1",
            note_date=date(2026, 4, 2),
            items=(VatBookingItem("6100", Decimal("30.00"), 0),), vat_accounts=VAT,
        )
        invoice_id = UUID(session.query(VerbindlichkeitsOP.open_item_id)
                          .filter_by(invoice_id=str(invoice.invoice_id)).scalar())
        credit_id = UUID(session.query(GuthabenOP.open_item_id)
                         .filter_by(credit_note_id=str(note.credit_note_id)).scalar())
        offsets.post_offset(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            direction=OffsetDirection.SUPPLIER, invoice_open_item_id=invoice_id,
            credit_open_item_id=credit_id, amount=Decimal("30.00"),
            settlement_date=date(2026, 4, 11), booking_date=date(2026, 4, 11),
        )
        report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 11)
        )
        by_role = {row.role: row for row in report.rows}
        assert by_role["SUPPLIER_PAYABLES"].ledger_balance == Decimal("89.00")
        assert by_role["SUPPLIER_PAYABLES"].open_item_balance == Decimal("89.00")
        assert by_role["SUPPLIER_CREDIT_BALANCES"].ledger_balance == Decimal("0.00")
        assert by_role["SUPPLIER_CREDIT_BALANCES"].open_item_balance == Decimal("0.00")
    finally:
        session.close()
        engine.dispose()


def test_reconciliation_keeps_historically_used_control_accounts_separate():
    engine, session, company, partner, invoices, _payables, _payments, _credits, _offsets, _corrections = _environment()
    try:
        _invoice(invoices, company, partner, number="AR-OLD")
        role = session.query(Kontenrolle).filter_by(
            mandant_id=session.query(Mandant).filter_by(company_id=str(company.company_id)).one().id,
            role="CUSTOMER_RECEIVABLES",
        ).one()
        role.account_number = "1210"
        session.commit()
        _invoice(invoices, company, partner, number="AR-NEW")
        report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 1)
        )
        customer_rows = [row for row in report.rows if row.role == "CUSTOMER_RECEIVABLES"]
        assert {row.account_number for row in customer_rows} == {"1200", "1210"}
        assert all(row.difference == Decimal("0.00") for row in customer_rows)
        assert {row.status for row in customer_rows} == {
            "ABGESTIMMT", "KONTO_NICHT_MEHR_ZUGEORDNET"
        }
    finally:
        session.close()
        engine.dispose()


def test_payment_allocation_correction_reconciles_without_extra_booking():
    engine, session, company, partner, invoices, _payables, payments, _credits, _offsets, corrections = _environment()
    try:
        source = _invoice(invoices, company, partner, number="AR-SOURCE")
        target = _invoice(invoices, company, partner, number="AR-TARGET")
        payment = payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=_open_id(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("50.00"), payment_date=date(2026, 4, 10),
            booking_date=date(2026, 4, 10), cash_bank_account_number="1000",
        )
        event_id = UUID(session.query(RechnungsOPZahlungsereignis.event_id)
                        .filter_by(payment_id=str(payment.payment_id)).scalar())
        bookings_before = session.query(Buchung).count()
        corrections.correct(
            company_id=company.company_id, fiscal_year=FY26, original_event_id=event_id,
            target_open_item_id=_open_id(session, target), amount=Decimal("20.00"),
            correction_date=date(2026, 4, 11), booking_date=date(2026, 4, 12),
            reason="Zuordnung berichtigt", confirmed=True,
        )
        stored = session.query(Zahlungszuordnungskorrektur).one()
        assert stored.correction_date == date(2026, 4, 11)
        assert stored.booking_date == date(2026, 4, 12)
        assert stored.booking_id is None
        before = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 11)
        )
        after = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 12)
        )
        before_receivables = next(row for row in before.rows if row.role == "CUSTOMER_RECEIVABLES")
        after_receivables = next(row for row in after.rows if row.role == "CUSTOMER_RECEIVABLES")
        assert before_receivables.ledger_balance == Decimal("188.00")
        assert before_receivables.open_item_balance == Decimal("188.00")
        assert after_receivables.ledger_balance == Decimal("188.00")
        assert after_receivables.open_item_balance == Decimal("188.00")
        # On a shared control account the two allocation events net to zero;
        # verify the cutoff predicate independently as well.
        assert _correction_balance_adjustment(
            amount_delta=Decimal("-20.00"), booking_date=stored.booking_date,
            as_of_date=date(2026, 4, 11),
        ) == Decimal("0.00")
        assert _correction_balance_adjustment(
            amount_delta=Decimal("-20.00"), booking_date=stored.booking_date,
            as_of_date=date(2026, 4, 12),
        ) == Decimal("20.00")
        # Same-account allocation corrections carry no additional GL entry.
        assert session.query(Buchung).count() == bookings_before
        assert session.query(Zahlung).one().payment_id == str(payment.payment_id)
        bank_balance = sum(
            (line.amount if line.side == EntrySide.DEBIT.value else -line.amount)
            for line in session.query(Buchungszeile).filter_by(account_number="1000").all()
        )
        assert bank_balance == Decimal("50.00")
    finally:
        session.close()
        engine.dispose()


def test_rejects_out_of_year_booking_date_without_account_reclassification():
    engine, session, company, partner, invoices, _payables, payments, _credits, _offsets, corrections = _environment()
    try:
        source = _invoice(invoices, company, partner, number="AR-SOURCE-YEAR")
        target = _invoice(invoices, company, partner, number="AR-TARGET-YEAR")
        payment = payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=_open_id(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("20.00"), payment_date=date(2026, 4, 10),
            booking_date=date(2026, 4, 10), cash_bank_account_number="1000",
        )
        event_id = UUID(session.query(RechnungsOPZahlungsereignis.event_id)
                        .filter_by(payment_id=str(payment.payment_id)).scalar())
        bookings_before = session.query(Buchung).count()
        with pytest.raises(ValueError, match="Buchungsdatum"):
            corrections.correct(
                company_id=company.company_id, fiscal_year=FY26,
                original_event_id=event_id, target_open_item_id=_open_id(session, target),
                amount=Decimal("10.00"), correction_date=date(2026, 4, 11),
                booking_date=date(2027, 1, 2), reason="Datum außerhalb des Jahres",
                confirmed=True,
            )
        assert session.query(Zahlungszuordnungskorrektur).count() == 0
        assert session.query(Buchung).count() == bookings_before
        assert session.query(Zahlung).one().payment_id == str(payment.payment_id)
    finally:
        session.close()
        engine.dispose()


def test_legacy_correction_without_booking_date_is_temporally_unresolved():
    engine, session, company, partner, invoices, _payables, payments, _credits, _offsets, corrections = _environment()
    try:
        source = _invoice(invoices, company, partner, number="AR-SOURCE-LEGACY")
        target = _invoice(invoices, company, partner, number="AR-TARGET-LEGACY")
        payment = payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=_open_id(session, source), direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("20.00"), payment_date=date(2026, 4, 10),
            booking_date=date(2026, 4, 10), cash_bank_account_number="1000",
        )
        event_id = UUID(session.query(RechnungsOPZahlungsereignis.event_id)
                        .filter_by(payment_id=str(payment.payment_id)).scalar())
        corrections.correct(
            company_id=company.company_id, fiscal_year=FY26, original_event_id=event_id,
            target_open_item_id=_open_id(session, target), amount=Decimal("10.00"),
            correction_date=date(2026, 4, 11), booking_date=date(2026, 4, 12),
            reason="Historische Korrektur ohne Datum", confirmed=True,
        )
        stored = session.query(Zahlungszuordnungskorrektur).one()
        stored.booking_date = None  # legacy row as retained by the migration
        session.commit()
        report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 4, 11)
        )
        receivables = next(row for row in report.rows if row.role == "CUSTOMER_RECEIVABLES")
        assert receivables.difference == Decimal("0.00")
        assert receivables.status == "ZEITLICH_UNGEKLAERT"
        assert len(receivables.unresolved_correction_timings) == 1
        assert receivables.unresolved_correction_timings[0].reason == "Historische Korrektur ohne Datum"
        assert receivables.unresolved_correction_timings[0].correction_date == date(2026, 4, 11)
        assert session.query(Zahlung).one().payment_id == str(payment.payment_id)
        assert session.query(Buchung).filter_by(booking_id=str(payment.booking_id)).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_closed_prior_year_reconciliation_is_unchanged_after_next_year_payment():
    engine, session, company, partner, invoices, _payables, payments, _credits, _offsets, _corrections = _environment()
    try:
        invoice = _invoice(
            invoices, company, partner, year=FY25,
            booking_date=date(2025, 10, 15), number="AR-2025-1",
        )
        # Build the same year-end statements and invoke the application's
        # persistent closing workflow on the booked 2025 data.
        assets, liabilities = create_hgb_balance_sheet_structure()
        income_root = create_hgb_income_statement_structure()
        position_provider = HgbFinancialStatementPositionProvider(
            (assets, liabilities, income_root)
        )
        chart_path = Path(__file__).resolve().parents[2] / "src" / "simpleob" / "resources" / "chart_of_accounts" / "openbilanz_standard.csv"
        chart = CsvChartOfAccountsImporter(position_provider=position_provider).load(chart_path)
        ledger = Ledger()
        journal = Journal()
        posting = PostingService()
        for booking in BookingRepository(session).list_for_fiscal_year(
            company_id=company.company_id, fiscal_year=FY25
        ):
            posting.post_booking(booking=booking, journal=journal, ledger=ledger)
        account_types = {account.account_number: account.account_type for account in chart.accounts}
        balances = tuple(
            balance for balance in ledger.balances()
            if account_types.get(balance.account_number) in (AccountType.REVENUE, AccountType.EXPENSE)
        )
        builder = FinancialStatementBuilder(AccountMapper(chart))
        income_statement = IncomeStatement(
            income_statement=income_root,
            amounts=builder.build(balances=balances, root_positions=(income_root,)),
        )
        closing = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=BookingRepository(session),
            company_repository=CompanyRepository(session),
            closing_service=ClosingService(
                closing_accounts=ClosingAccounts(
                    income_summary_account="8990", profit_account="8020", loss_account="8021"
                )
            ),
        )
        closing.close(
            company_id=company.company_id, fiscal_year=FY25,
            income_statement=income_statement, ledger=ledger,
            chart_of_accounts=chart, closing_date=date(2025, 12, 31),
        )
        FiscalYearOpeningWorkflow(
            session=session,
            booking_repository=BookingRepository(session),
            company_repository=CompanyRepository(session),
            transfer_service=FiscalYearTransferService(
                opening_balance_account_number="9000", profit_account_number="8020",
                loss_account_number="8021", profit_loss_carryforward_account_number="2970",
            ),
            posting_service=PostingService(),
        ).open(
            company_id=company.company_id, source_fiscal_year=FY25,
            target_fiscal_year=FY26,
            account_types={account.account_number: account.account_type for account in chart.accounts},
        )
        count_after_open = session.query(Buchung).count()
        old_report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2025, 12, 31)
        )
        assert old_report.rows[0].ledger_balance == Decimal("119.00")
        assert old_report.rows[0].open_item_balance == Decimal("119.00")
        session.expire_all()
        op_id = _open_id(session, invoice)
        payments.post_payment(
            company_id=company.company_id, fiscal_year=FY26, partner_id=partner.partner_id,
            open_item_id=op_id, direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount=Decimal("119.00"), payment_date=date(2026, 2, 5),
            booking_date=date(2026, 2, 6), cash_bank_account_number="1000",
        )
        old_report_after = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2025, 12, 31)
        )
        later_report = OpenItemReconciliationRepository(session).reconcile(
            company_id=company.company_id, as_of_date=date(2026, 2, 6)
        )
        assert old_report_after == old_report
        assert session.query(Buchung).count() == count_after_open + 1
        assert later_report.rows[0].ledger_balance == Decimal("0.00")
        assert later_report.rows[0].open_item_balance == Decimal("0.00")
        assert session.query(Wirtschaftsjahr).filter_by(start_date=FY25.start_date).one().status == FiscalYearStatus.CLOSED.value
    finally:
        session.close()
        engine.dispose()
