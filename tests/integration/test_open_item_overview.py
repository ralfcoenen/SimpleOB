"""Integrationstests für die aktuelle OP-Übersicht."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, func, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

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
    GuthabenOPEreignis,
    Kontenrolle,
    Konto,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPStorno,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
    Zahlungszuordnungskorrektur,
    Zahlungszuordnungskorrekturereignis,
)
from simpleob.database.open_item_invoice_cancellation_repository import (
    OpenItemInvoiceCancellationRepository,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.database.open_item_overview_repository import OpenItemOverviewRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
from simpleob.database.open_item_reconciliation_repository import (
    OpenItemReconciliationRepository,
)
from simpleob.database.payable_invoice_repository import PayableInvoiceRepository
from simpleob.database.payment_allocation_correction_repository import (
    PaymentAllocationCorrectionRepository,
)
from simpleob.database.receivable_invoice_repository import ReceivableInvoiceRepository
from simpleob.domain.account_type import AccountType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.domain.open_item_overview import OpenItemKind
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.credit_note_posting_service import CreditNotePostingService
from simpleob.services.open_item_invoice_cancellation_service import (
    OpenItemInvoiceCancellationService,
)
from simpleob.services.open_item_offset_service import OpenItemOffsetService
from simpleob.services.open_item_overview_service import OpenItemOverviewService
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

FY25 = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
FY26 = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
VAT = VatAccounts("1576", "1570", "1776", "1770")


def _environment(
    database_url="sqlite:///:memory:",
    *,
    engine=None,
    session_factory=Session,
    create_schema=True,
):
    engine = engine or create_engine(database_url)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        if engine.dialect.name == "sqlite":
            connection.execute("PRAGMA foreign_keys=ON")

    if create_schema:
        Base.metadata.create_all(engine)
    session = session_factory(bind=engine)
    companies = CompanyRepository(session)
    company = Company(uuid4(), "OP Overview UG")
    other_company = Company(uuid4(), "Andere OP Overview UG")
    for current in (company, other_company):
        companies.add(current)
        companies.add_fiscal_year(current.company_id, FY25)
        companies.add_fiscal_year(current.company_id, FY26)

    accounts = (
        ("1000", "Bank", AccountType.ASSET),
        ("1200", "Kundenforderungen", AccountType.ASSET),
        ("3300", "Lieferantenverbindlichkeiten", AccountType.LIABILITY),
        ("2400", "Kundenguthaben", AccountType.LIABILITY),
        ("1300", "Lieferantenguthaben", AccountType.ASSET),
        ("8400", "Erlöse", AccountType.REVENUE),
        ("6100", "Aufwand", AccountType.EXPENSE),
        ("1576", "Vorsteuer", AccountType.ASSET),
        ("1570", "Vorsteuer ermäßigt", AccountType.ASSET),
        ("1776", "Umsatzsteuer", AccountType.LIABILITY),
        ("1770", "Umsatzsteuer ermäßigt", AccountType.LIABILITY),
    )
    for current in (company, other_company):
        mandate = session.query(Mandant).filter_by(
            company_id=str(current.company_id)
        ).one()
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
        session.add_all(
            Kontenrolle(
                mandant_id=mandate.id,
                role=role,
                account_number=number,
            )
            for role, number in (
                ("BANK", "1000"),
                ("CUSTOMER_RECEIVABLES", "1200"),
                ("SUPPLIER_PAYABLES", "3300"),
                ("CUSTOMER_CREDIT_BALANCES", "2400"),
                ("SUPPLIER_CREDIT_BALANCES", "1300"),
            )
        )
    session.commit()

    partners = BusinessPartnerRepository(session)
    partner = BusinessPartner(
        company.company_id,
        "Kunde und Lieferant GmbH",
        is_customer=True,
        is_supplier=True,
    )
    other_partner = BusinessPartner(
        other_company.company_id,
        "Fremdmandant GmbH",
        is_customer=True,
        is_supplier=True,
    )
    partners.add(partner)
    partners.add(other_partner)
    booking_repository = BookingRepository(session)
    chart = ChartOfAccountsRepository(session)
    receivables = ReceivableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partners,
        invoice_repository=ReceivableInvoiceRepository(session),
        chart_of_accounts_repository=chart,
    )
    payables = PayableInvoicePostingService(
        booking_repository=booking_repository,
        partner_repository=partners,
        invoice_repository=PayableInvoiceRepository(session),
        chart_of_accounts_repository=chart,
    )
    payments = OpenItemPaymentService(
        booking_repository=booking_repository,
        payment_repository=OpenItemPaymentRepository(session),
        chart_of_accounts_repository=chart,
    )
    credits = CreditNotePostingService(
        booking_repository=booking_repository,
        partner_repository=partners,
        credit_note_repository=CreditNoteRepository(session),
        chart_of_accounts_repository=chart,
    )
    offsets = OpenItemOffsetService(
        booking_repository=booking_repository,
        offset_repository=OpenItemOffsetRepository(session),
    )
    corrections = PaymentAllocationCorrectionService(
        booking_repository=booking_repository,
        correction_repository=PaymentAllocationCorrectionRepository(session),
        offset_repository=OpenItemOffsetRepository(session),
        payment_repository=OpenItemPaymentRepository(session),
    )
    overview = OpenItemOverviewService(OpenItemOverviewRepository(session))
    return (
        engine,
        session,
        company,
        other_company,
        partner,
        other_partner,
        receivables,
        payables,
        payments,
        credits,
        offsets,
        corrections,
        overview,
    )


def _invoice(service, company, partner, *, year, number, date_value, supplier=False):
    values = dict(
        company_id=company.company_id,
        fiscal_year=year,
        partner_id=partner.partner_id,
        invoice_number=number,
        booking_date=date_value,
        due_date=date(date_value.year, 12, 31),
        items=(
            VatBookingItem(
                "6100" if supplier else "8400",
                Decimal("119.00"),
                0,
            ),
        ),
        vat_accounts=VAT,
    )
    if supplier:
        return service.post_supplier_invoice_on_account(**values)
    return service.post_output_invoice_on_account(**values)


def _open_id(session, model, *, foreign_key, foreign_id):
    return UUID(
        session.query(model.open_item_id)
        .filter(getattr(model, foreign_key) == str(foreign_id))
        .scalar()
    )


def _post_payment(
    service,
    company,
    partner,
    open_item_id,
    *,
    direction,
    amount,
    booking_date,
):
    return service.post_payment(
        company_id=company.company_id,
        fiscal_year=FY26,
        partner_id=partner.partner_id,
        open_item_id=open_item_id,
        direction=direction,
        amount=Decimal(amount),
        payment_date=booking_date,
        booking_date=booking_date,
        cash_bank_account_number="1000",
    )


def _credit(services, company, partner, *, number, amount, supplier=False):
    method = (
        services.post_supplier_credit_note
        if supplier
        else services.post_customer_credit_note
    )
    return method(
        company_id=company.company_id,
        fiscal_year=FY26,
        partner_id=partner.partner_id,
        note_number=number,
        note_date=date(2026, 3, 1),
        items=(
            VatBookingItem(
                "6100" if supplier else "8400",
                Decimal(amount),
                0,
            ),
        ),
        vat_accounts=VAT,
    )


def _offset(
    service,
    company,
    partner,
    *,
    invoice_id,
    credit_id,
    amount,
    direction,
):
    return service.post_offset(
        company_id=company.company_id,
        fiscal_year=FY26,
        partner_id=partner.partner_id,
        direction=direction,
        invoice_open_item_id=invoice_id,
        credit_open_item_id=credit_id,
        amount=Decimal(amount),
        settlement_date=date(2026, 4, 10),
        booking_date=date(2026, 4, 11),
    )


def test_overview_covers_four_kinds_settlements_corrections_and_tenant_isolation():
    (
        engine,
        session,
        company,
        other_company,
        partner,
        other_partner,
        receivables,
        payables,
        payments,
        credits,
        offsets,
        corrections,
        overview,
    ) = _environment()
    try:
        old_receivable = _invoice(
            receivables,
            company,
            partner,
            year=FY25,
            number="AR-OLD",
            date_value=date(2025, 11, 1),
        )
        old_payable = _invoice(
            payables,
            company,
            partner,
            year=FY25,
            number="AP-OLD",
            date_value=date(2025, 11, 2),
            supplier=True,
        )
        session.query(Wirtschaftsjahr).filter(
            Wirtschaftsjahr.start_date == FY25.start_date,
            Wirtschaftsjahr.mandant_id
            == session.query(Mandant.id)
            .filter(Mandant.company_id == str(company.company_id))
            .scalar_subquery(),
        ).update({Wirtschaftsjahr.status: FiscalYearStatus.CLOSED.value})
        session.commit()

        old_receivable_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=old_receivable.invoice_id,
        )
        old_payable_id = _open_id(
            session,
            VerbindlichkeitsOP,
            foreign_key="invoice_id",
            foreign_id=old_payable.invoice_id,
        )
        first_payment = _post_payment(
            payments,
            company,
            partner,
            old_receivable_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="30.00",
            booking_date=date(2026, 1, 10),
        )
        _post_payment(
            payments,
            company,
            partner,
            old_receivable_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="20.00",
            booking_date=date(2026, 2, 10),
        )
        target_receivable = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-TARGET",
            date_value=date(2026, 2, 1),
        )
        target_receivable_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=target_receivable.invoice_id,
        )
        original_payment_event_id = UUID(
            session.query(RechnungsOPZahlungsereignis.event_id)
            .filter(
                RechnungsOPZahlungsereignis.payment_id
                == str(first_payment.payment_id)
            )
            .scalar()
        )
        corrections.correct(
            company_id=company.company_id,
            fiscal_year=FY26,
            original_event_id=original_payment_event_id,
            target_open_item_id=target_receivable_id,
            amount=Decimal("10.00"),
            correction_date=date(2026, 2, 15),
            booking_date=date(2026, 2, 15),
            reason="Teilbetrag auf Zielrechnung übertragen",
            confirmed=True,
        )
        customer_credit = _credit(
            credits,
            company,
            partner,
            number="CN-CUSTOMER",
            amount="40.00",
        )
        customer_credit_id = _open_id(
            session,
            GuthabenOP,
            foreign_key="credit_note_id",
            foreign_id=customer_credit.credit_note_id,
        )
        _offset(
            offsets,
            company,
            partner,
            invoice_id=old_receivable_id,
            credit_id=customer_credit_id,
            amount="20.00",
            direction=OffsetDirection.CUSTOMER,
        )

        full_receivable = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-FULL",
            date_value=date(2026, 3, 1),
        )
        full_receivable_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=full_receivable.invoice_id,
        )
        _post_payment(
            payments,
            company,
            partner,
            full_receivable_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="119.00",
            booking_date=date(2026, 3, 2),
        )
        closed_customer_credit_invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-CREDIT-CLOSED",
            date_value=date(2026, 3, 3),
        )
        closed_customer_credit = _credit(
            credits,
            company,
            partner,
            number="CN-CUSTOMER-FULL",
            amount="12.00",
        )
        _offset(
            offsets,
            company,
            partner,
            invoice_id=_open_id(
                session,
                ForderungsOP,
                foreign_key="invoice_id",
                foreign_id=closed_customer_credit_invoice.invoice_id,
            ),
            credit_id=_open_id(
                session,
                GuthabenOP,
                foreign_key="credit_note_id",
                foreign_id=closed_customer_credit.credit_note_id,
            ),
            amount="12.00",
            direction=OffsetDirection.CUSTOMER,
        )

        _post_payment(
            payments,
            company,
            partner,
            old_payable_id,
            direction=PaymentDirection.SUPPLIER_PAYMENT,
            amount="10.00",
            booking_date=date(2026, 1, 12),
        )
        supplier_credit = _credit(
            credits,
            company,
            partner,
            number="CN-SUPPLIER",
            amount="30.00",
            supplier=True,
        )
        supplier_credit_id = _open_id(
            session,
            GuthabenOP,
            foreign_key="credit_note_id",
            foreign_id=supplier_credit.credit_note_id,
        )
        _offset(
            offsets,
            company,
            partner,
            invoice_id=old_payable_id,
            credit_id=supplier_credit_id,
            amount="15.00",
            direction=OffsetDirection.SUPPLIER,
        )
        full_payable = _invoice(
            payables,
            company,
            partner,
            year=FY26,
            number="AP-FULL",
            date_value=date(2026, 3, 4),
            supplier=True,
        )
        full_payable_id = _open_id(
            session,
            VerbindlichkeitsOP,
            foreign_key="invoice_id",
            foreign_id=full_payable.invoice_id,
        )
        _post_payment(
            payments,
            company,
            partner,
            full_payable_id,
            direction=PaymentDirection.SUPPLIER_PAYMENT,
            amount="119.00",
            booking_date=date(2026, 3, 5),
        )
        closed_supplier_credit_invoice = _invoice(
            payables,
            company,
            partner,
            year=FY26,
            number="AP-CREDIT-CLOSED",
            date_value=date(2026, 3, 6),
            supplier=True,
        )
        closed_supplier_credit = _credit(
            credits,
            company,
            partner,
            number="CN-SUPPLIER-FULL",
            amount="9.00",
            supplier=True,
        )
        _offset(
            offsets,
            company,
            partner,
            invoice_id=_open_id(
                session,
                VerbindlichkeitsOP,
                foreign_key="invoice_id",
                foreign_id=closed_supplier_credit_invoice.invoice_id,
            ),
            credit_id=_open_id(
                session,
                GuthabenOP,
                foreign_key="credit_note_id",
                foreign_id=closed_supplier_credit.credit_note_id,
            ),
            amount="9.00",
            direction=OffsetDirection.SUPPLIER,
        )

        _invoice(
            receivables,
            other_company,
            other_partner,
            year=FY26,
            number="OTHER-AR",
            date_value=date(2026, 3, 7),
        )

        counts_before = _stored_counts(session)
        report = overview.list_items(company_id=company.company_id)
        by_number = {item.document_number: item for item in report.items}
        assert set(by_number) == {
            "AR-OLD",
            "AR-TARGET",
            "AR-CREDIT-CLOSED",
            "CN-CUSTOMER",
            "AP-OLD",
            "AP-CREDIT-CLOSED",
            "CN-SUPPLIER",
        }
        assert by_number["AR-OLD"].kind is OpenItemKind.CUSTOMER_RECEIVABLE
        assert by_number["AR-OLD"].document_date == date(2025, 11, 1)
        assert by_number["AR-OLD"].booking_date == date(2025, 11, 1)
        assert by_number["AR-OLD"].original_amount == Decimal("119.00")
        assert by_number["AR-OLD"].payments_amount == Decimal("40.00")
        assert by_number["AR-OLD"].offsets_amount == Decimal("20.00")
        assert by_number["AR-OLD"].open_amount == Decimal("59.00")
        assert by_number["AR-TARGET"].payments_amount == Decimal("10.00")
        assert by_number["AR-TARGET"].open_amount == Decimal("109.00")
        assert by_number["CN-CUSTOMER"].open_amount == Decimal("20.00")
        assert by_number["CN-CUSTOMER"].offsets_amount == Decimal("20.00")
        assert by_number["AP-OLD"].kind is OpenItemKind.SUPPLIER_PAYABLE
        assert by_number["AP-OLD"].payments_amount == Decimal("10.00")
        assert by_number["AP-OLD"].offsets_amount == Decimal("15.00")
        assert by_number["AP-OLD"].open_amount == Decimal("94.00")
        assert by_number["CN-SUPPLIER"].kind is OpenItemKind.SUPPLIER_CREDIT
        assert by_number["CN-SUPPLIER"].open_amount == Decimal("15.00")
        assert report.partners == (
            type(report.partners[0])(partner.partner_id, partner.name),
        )

        detail = overview.get_detail(
            company_id=company.company_id,
            open_item_id=by_number["AR-OLD"].open_item_id,
        )
        assert detail is not None
        assert [activity.kind.value for activity in detail.activities].count("PAYMENT") == 2
        payment_activities = [
            activity
            for activity in detail.activities
            if activity.kind.value == "PAYMENT"
        ]
        assert all("Kunde und Lieferant GmbH" in activity.reference for activity in payment_activities)
        assert all("Rechnung AR-OLD" in activity.reference for activity in payment_activities)
        assert all(str(first_payment.payment_id) not in activity.reference for activity in payment_activities)
        offset_activity = next(
            activity
            for activity in detail.activities
            if activity.kind.value == "OFFSET"
        )
        assert "Gutschrift CN-CUSTOMER" in offset_activity.reference
        corrections_in_detail = [
            activity
            for activity in detail.activities
            if activity.kind.value == "PAYMENT_CORRECTION"
        ]
        assert len(corrections_in_detail) == 1
        assert corrections_in_detail[0].amount == Decimal("-10.00")
        assert "Kunde und Lieferant GmbH" in corrections_in_detail[0].reference
        assert "Rechnung AR-OLD" in corrections_in_detail[0].reference
        assert "ursprüngliche Zahlung 10.01.2026" in corrections_in_detail[0].reference
        assert "Rechnung AR-TARGET" in corrections_in_detail[0].description
        assert "Buchung der ursprünglichen Zahlung 10.01.2026" in corrections_in_detail[0].description
        assert str(first_payment.payment_id) not in corrections_in_detail[0].reference
        assert _stored_counts(session) == counts_before

        credit_detail = overview.get_detail(
            company_id=company.company_id,
            open_item_id=by_number["CN-CUSTOMER"].open_item_id,
        )
        assert credit_detail is not None
        credit_offset = next(
            activity
            for activity in credit_detail.activities
            if activity.kind.value == "OFFSET"
        )
        assert "Gutschrift CN-CUSTOMER" in credit_offset.reference
        assert "Rechnung AR-OLD" in credit_offset.reference
        assert "Kunde und Lieferant GmbH" in credit_offset.description
        assert _stored_counts(session) == counts_before

        all_items = overview.list_items(
            company_id=company.company_id,
            include_settled=True,
        ).items
        settled = {item.document_number: item for item in all_items if item.open_amount == 0}
        assert set(settled) == {
            "AR-FULL",
            "AP-FULL",
            "CN-CUSTOMER-FULL",
            "CN-SUPPLIER-FULL",
        }
        assert all(item.company_id == company.company_id for item in all_items)
        assert "OTHER-AR" not in {item.document_number for item in all_items}
        assert all(item.partner_id == partner.partner_id for item in report.items)
        assert _stored_counts(session) == counts_before
    finally:
        session.close()
        engine.dispose()


def _stored_counts(session: Session) -> tuple[int, ...]:
    models = (
        Buchung,
        Buchungszeile,
        ForderungsOP,
        VerbindlichkeitsOP,
        GuthabenOP,
        Zahlung,
        RechnungsOPZahlungsereignis,
        OPGuthabenverrechnung,
        RechnungsOPVerrechnungsereignis,
        GuthabenOPEreignis,
        Zahlungszuordnungskorrektur,
        Zahlungszuordnungskorrekturereignis,
        RechnungsOPStorno,
    )
    return tuple(session.query(model).count() for model in models)


@pytest.mark.parametrize("supplier", (False, True), ids=("customer", "supplier"))
def test_unpaid_invoice_cancellation_mirrors_booking_and_reconciles_by_date(supplier):
    (
        engine,
        session,
        company,
        _other_company,
        partner,
        _other_partner,
        receivables,
        payables,
        _payments,
        _credits,
        _offsets,
        _corrections,
        overview,
    ) = _environment()
    booking_repository = BookingRepository(session)
    service = OpenItemInvoiceCancellationService(
        OpenItemInvoiceCancellationRepository(
            session=session,
            booking_repository=booking_repository,
        )
    )
    reconciliation = OpenItemReconciliationRepository(session)
    try:
        invoice = _invoice(
            payables if supplier else receivables,
            company,
            partner,
            year=FY26,
            number="AP-STORNO" if supplier else "AR-STORNO",
            date_value=date(2026, 3, 1),
            supplier=supplier,
        )
        op_model = VerbindlichkeitsOP if supplier else ForderungsOP
        open_item_id = _open_id(
            session,
            op_model,
            foreign_key="invoice_id",
            foreign_id=invoice.invoice_id,
        )
        role = "SUPPLIER_PAYABLES" if supplier else "CUSTOMER_RECEIVABLES"
        preview = service.preview(
            company_id=company.company_id,
            fiscal_year=FY26,
            open_item_id=open_item_id,
        )
        original_lines = tuple(preview.original_booking.lines)
        bookings_before = session.query(Buchung).count()
        service.cancel_invoice(
            company_id=company.company_id,
            fiscal_year=FY26,
            open_item_id=open_item_id,
            booking_date=date(2026, 4, 15),
            reason="Rechnung fehlerhaft",
            confirmed=True,
        )
        storno = session.query(RechnungsOPStorno).one()
        reversal = session.query(Buchung).filter_by(booking_id=storno.booking_id).one()
        actual_lines = tuple(
            (line.account_number, line.side, Decimal(line.amount))
            for line in sorted(reversal.zeilen, key=lambda row: row.position)
        )
        expected_lines = tuple(
            (
                line.account_number,
                "CREDIT" if line.side.value == "DEBIT" else "DEBIT",
                line.amount,
            )
            for line in original_lines
        )
        assert actual_lines == expected_lines
        assert reversal.booking_type == "REVERSAL"
        assert reversal.reversal_of_booking_id == str(invoice.booking_id)
        assert session.query(Buchung).count() == bookings_before + 1
        assert "1000" not in {line.account_number for line in reversal.zeilen}
        assert session.query(Zahlung).count() == 0

        before = reconciliation.reconcile(
            company_id=company.company_id,
            as_of_date=date(2026, 4, 14),
        )
        after = reconciliation.reconcile(
            company_id=company.company_id,
            as_of_date=date(2026, 4, 15),
        )
        assert next(row for row in before.rows if row.role == role).open_item_balance == Decimal("119.00")
        reconciled = next(row for row in after.rows if row.role == role)
        assert reconciled.open_item_balance == Decimal("0.00")
        assert reconciled.ledger_balance == Decimal("0.00")
        assert reconciled.status == "ABGESTIMMT"

        all_items = overview.list_items(
            company_id=company.company_id,
            include_settled=True,
        ).items
        canceled_item = next(item for item in all_items if item.open_item_id == open_item_id)
        assert canceled_item.open_amount == Decimal("0.00")
        assert canceled_item.payments_amount == Decimal("0.00")
        detail = overview.get_detail(
            company_id=company.company_id,
            open_item_id=open_item_id,
        )
        assert detail is not None
        activity = next(
            item for item in detail.activities
            if item.kind.value == "INVOICE_CANCELLATION"
        )
        assert activity.booking_date == date(2026, 4, 15)
        assert activity.amount == Decimal("-119.00")
        assert "Rechnung fehlerhaft" in activity.description
        assert str(storno.booking_id) not in activity.description
        assert session.query(RechnungsOPZahlungsereignis).count() == 0
        with pytest.raises(ValueError, match="bereits storniert|Gegenbuchung"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=open_item_id,
                booking_date=date(2026, 4, 16),
                reason="Doppelversuch",
                confirmed=True,
            )
        assert session.query(RechnungsOPStorno).count() == 1
        assert session.query(Buchung).filter(
            Buchung.reversal_of_booking_id == str(invoice.booking_id)
        ).count() == 1
    finally:
        session.close()
        engine.dispose()


def test_invoice_cancellation_rejects_payment_history_and_rolls_back_failed_write(monkeypatch):
    (
        engine,
        session,
        company,
        _other_company,
        partner,
        _other_partner,
        receivables,
        _payables,
        payments,
        _credits,
        _offsets,
        _corrections,
        _overview,
    ) = _environment()
    booking_repository = BookingRepository(session)
    service = OpenItemInvoiceCancellationService(
        OpenItemInvoiceCancellationRepository(
            session=session,
            booking_repository=booking_repository,
        )
    )
    try:
        invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-PAID-HISTORY",
            date_value=date(2026, 3, 1),
        )
        open_item_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=invoice.invoice_id,
        )
        _post_payment(
            payments,
            company,
            partner,
            open_item_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="1.00",
            booking_date=date(2026, 3, 2),
        )
        counts = _stored_counts(session)
        with pytest.raises(ValueError, match="Zahlungshistorie"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=open_item_id,
                booking_date=date(2026, 4, 1),
                reason="Nicht zulässig",
                confirmed=True,
            )
        assert _stored_counts(session) == counts

        unpaid = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-ROLLBACK",
            date_value=date(2026, 4, 2),
        )
        unpaid_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=unpaid.invoice_id,
        )
        before_failed_write = session.query(Buchung).count(), session.query(RechnungsOPStorno).count()
        monkeypatch.setattr(
            booking_repository,
            "commit",
            lambda: (_ for _ in ()).throw(RuntimeError("simulierter Commitfehler")),
        )
        with pytest.raises(RuntimeError, match="simulierter Commitfehler"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=unpaid_id,
                booking_date=date(2026, 4, 3),
                reason="Rollback testen",
                confirmed=True,
            )
        assert (session.query(Buchung).count(), session.query(RechnungsOPStorno).count()) == before_failed_write
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("history_kind", ("offset", "correction"))
def test_invoice_cancellation_rejects_offset_and_correction_history(history_kind):
    (
        engine,
        session,
        company,
        _other_company,
        partner,
        _other_partner,
        receivables,
        _payables,
        payments,
        credits,
        offsets,
        corrections,
        _overview,
    ) = _environment()
    service = OpenItemInvoiceCancellationService(
        OpenItemInvoiceCancellationRepository(
            session=session,
            booking_repository=BookingRepository(session),
        )
    )
    try:
        invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number=f"AR-{history_kind.upper()}-HISTORY",
            date_value=date(2026, 3, 1),
        )
        source_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=invoice.invoice_id,
        )
        if history_kind == "offset":
            credit = _credit(
                credits,
                company,
                partner,
                number="CN-HISTORY",
                amount="1.00",
            )
            credit_id = _open_id(
                session,
                GuthabenOP,
                foreign_key="credit_note_id",
                foreign_id=credit.credit_note_id,
            )
            _offset(
                offsets,
                company,
                partner,
                invoice_id=source_id,
                credit_id=credit_id,
                amount="1.00",
                direction=OffsetDirection.CUSTOMER,
            )
            expected = "Verrechnungshistorie"
        else:
            payment = _post_payment(
                payments,
                company,
                partner,
                source_id,
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount="1.00",
                booking_date=date(2026, 3, 2),
            )
            event_id = UUID(
                session.query(RechnungsOPZahlungsereignis.event_id)
                .filter_by(payment_id=str(payment.payment_id))
                .scalar()
            )
            target_invoice = _invoice(
                receivables,
                company,
                partner,
                year=FY26,
                number="AR-CORRECTION-TARGET",
                date_value=date(2026, 3, 3),
            )
            target_id = _open_id(
                session,
                ForderungsOP,
                foreign_key="invoice_id",
                foreign_id=target_invoice.invoice_id,
            )
            corrections.correct(
                company_id=company.company_id,
                fiscal_year=FY26,
                original_event_id=event_id,
                target_open_item_id=target_id,
                amount=Decimal("1.00"),
                correction_date=date(2026, 3, 4),
                booking_date=date(2026, 3, 4),
                reason="Falscher OP",
                confirmed=True,
            )
            expected = "Zahlungshistorie|Korrekturhistorie"
            assert session.query(Zahlungszuordnungskorrektur).count() == 1
        with pytest.raises(ValueError, match=expected):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=source_id,
                booking_date=date(2026, 4, 1),
                reason="Historie vorhanden",
                confirmed=True,
            )
        assert session.query(RechnungsOPStorno).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_invoice_cancellation_requires_same_open_fiscal_year_and_tenant():
    (
        engine,
        session,
        company,
        other_company,
        partner,
        other_partner,
        receivables,
        _payables,
        _payments,
        _credits,
        _offsets,
        _corrections,
        _overview,
    ) = _environment()
    repository = OpenItemInvoiceCancellationRepository(
        session=session,
        booking_repository=BookingRepository(session),
    )
    service = OpenItemInvoiceCancellationService(repository)
    try:
        invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-WRONG-YEAR",
            date_value=date(2026, 3, 1),
        )
        open_item_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=invoice.invoice_id,
        )
        with pytest.raises(ValueError, match="ausgewählten Geschäftsjahr"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY25,
                open_item_id=open_item_id,
                booking_date=date(2025, 12, 1),
                reason="Falsches Jahr",
                confirmed=True,
            )
        company_model = session.query(Mandant).filter_by(
            company_id=str(company.company_id)
        ).one()
        fiscal_year_model = session.query(Wirtschaftsjahr).filter_by(
            mandant_id=company_model.id,
            start_date=FY26.start_date,
        ).one()
        fiscal_year_model.status = FiscalYearStatus.CLOSED.value
        session.commit()
        with pytest.raises(ValueError, match="nicht offen"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=open_item_id,
                booking_date=date(2026, 4, 1),
                reason="Geschlossenes Jahr",
                confirmed=True,
            )
        fiscal_year_model.status = FiscalYearStatus.OPEN.value
        session.commit()
        other_invoice = _invoice(
            receivables,
            other_company,
            other_partner,
            year=FY26,
            number="OTHER-AR-STORNO",
            date_value=date(2026, 3, 1),
        )
        other_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=other_invoice.invoice_id,
        )
        with pytest.raises(ValueError, match="Mandanten"):
            service.preview(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=other_id,
            )
        assert session.query(RechnungsOPStorno).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_concurrent_invoice_cancellation_leaves_one_complete_reversal(tmp_path: Path):
    (
        engine,
        session,
        company,
        _other_company,
        partner,
        _other_partner,
        receivables,
        _payables,
        _payments,
        _credits,
        _offsets,
        _corrections,
        _overview,
    ) = _environment(f"sqlite:///{tmp_path / 'concurrent_storno.db'}")
    try:
        invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="AR-CONCURRENT",
            date_value=date(2026, 3, 1),
        )
        open_item_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=invoice.invoice_id,
        )
        session.close()
        barrier = Barrier(2)

        def cancel_from_independent_session():
            local_session = Session(engine)
            booking_repository = BookingRepository(local_session)
            repository = OpenItemInvoiceCancellationRepository(
                session=local_session,
                booking_repository=booking_repository,
            )
            original_load = repository._load_eligible_invoice

            def synchronized_load(**kwargs):
                result = original_load(**kwargs)
                if kwargs["for_update"]:
                    barrier.wait(timeout=5)
                return result

            repository._load_eligible_invoice = synchronized_load
            service = OpenItemInvoiceCancellationService(repository)
            try:
                service.cancel_invoice(
                    company_id=company.company_id,
                    fiscal_year=FY26,
                    open_item_id=open_item_id,
                    booking_date=date(2026, 4, 1),
                    reason="Paralleler Versuch",
                    confirmed=True,
                )
                return "ok"
            except Exception as error:
                return error
            finally:
                local_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                executor.map(
                    lambda _index: cancel_from_independent_session(),
                    range(2),
                )
            )
        assert results.count("ok") == 1
        assert sum(isinstance(result, Exception) for result in results) == 1
        verification = Session(engine)
        try:
            assert verification.query(RechnungsOPStorno).count() == 1
            assert verification.query(Buchung).filter(
                Buchung.reversal_of_booking_id == str(invoice.booking_id)
            ).count() == 1
        finally:
            verification.close()
    finally:
        session.close()
        engine.dispose()


def test_postgresql_cancels_customer_and_supplier_invoices_atomically(monkeypatch):
    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.database != "simpleob_migration_test"
        or url.host not in ("localhost", "127.0.0.1")
        or url.username != "simpleob_auth_test"
    ):
        pytest.fail(
            "Nur die lokale PostgreSQL-Testdatenbank simpleob_migration_test "
            "als simpleob_auth_test ist zulässig."
        )

    engine = create_engine(url)
    connection = engine.connect()
    transaction = connection.begin()
    session = None
    try:
        identity = connection.execute(
            text("SELECT current_database(), current_user")
        ).one()
        assert identity == ("simpleob_migration_test", "simpleob_auth_test")

        factory = sessionmaker(
            join_transaction_mode="create_savepoint",
        )
        environment = _environment(
            engine=engine,
            session_factory=lambda **kwargs: factory(bind=connection),
            create_schema=False,
        )
        (
            _engine,
            session,
            company,
            _other_company,
            partner,
            _other_partner,
            receivables,
            payables,
            _payments,
            _credits,
            _offsets,
            _corrections,
            _overview,
        ) = environment
        booking_repository = BookingRepository(session)
        service = OpenItemInvoiceCancellationService(
            OpenItemInvoiceCancellationRepository(
                session=session,
                booking_repository=booking_repository,
            )
        )

        foreign_invoice = _invoice(
            receivables,
            _other_company,
            _other_partner,
            year=FY26,
            number="PG-FOREIGN-AR",
            date_value=date(2026, 6, 1),
        )
        foreign_item_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=foreign_invoice.invoice_id,
        )
        with pytest.raises(ValueError):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=foreign_item_id,
                booking_date=date(2026, 6, 15),
                reason="Fremdmandantentest",
                confirmed=True,
            )
        assert session.query(RechnungsOPStorno).count() == 0

        for supplier, posting_service, invoice_number in (
            (False, receivables, "PG-AR-STORNO"),
            (True, payables, "PG-AP-STORNO"),
        ):
            invoice = _invoice(
                posting_service,
                company,
                partner,
                year=FY26,
                number=invoice_number,
                date_value=date(2026, 6, 1),
                supplier=supplier,
            )
            open_item_model = VerbindlichkeitsOP if supplier else ForderungsOP
            open_item_id = _open_id(
                session,
                open_item_model,
                foreign_key="invoice_id",
                foreign_id=invoice.invoice_id,
            )
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=open_item_id,
                booking_date=date(2026, 6, 15),
                reason="PostgreSQL-Integrationstest",
                confirmed=True,
            )

            storno = session.query(RechnungsOPStorno).filter_by(
                receivable_open_item_id=(None if supplier else str(open_item_id)),
                payable_open_item_id=(str(open_item_id) if supplier else None),
            ).one()
            reversal = session.query(Buchung).filter_by(
                booking_id=storno.booking_id
            ).one()
            assert reversal.reversal_of_booking_id == str(invoice.booking_id)
            assert reversal.booking_type == "REVERSAL"
            assert session.query(RechnungsOPStorno).filter_by(
                booking_id=reversal.booking_id
            ).count() == 1
            assert session.query(Buchung).filter_by(
                reversal_of_booking_id=str(invoice.booking_id)
            ).count() == 1

            with pytest.raises(ValueError):
                service.cancel_invoice(
                    company_id=company.company_id,
                    fiscal_year=FY26,
                    open_item_id=open_item_id,
                    booking_date=date(2026, 6, 16),
                    reason="Doppelstorno",
                    confirmed=True,
                )
            assert session.query(RechnungsOPStorno).filter_by(
                booking_id=reversal.booking_id
            ).count() == 1

        rollback_invoice = _invoice(
            receivables,
            company,
            partner,
            year=FY26,
            number="PG-ROLLBACK-AR",
            date_value=date(2026, 6, 2),
        )
        rollback_item_id = _open_id(
            session,
            ForderungsOP,
            foreign_key="invoice_id",
            foreign_id=rollback_invoice.invoice_id,
        )
        original_flush = session.flush

        def fail_flush(*_args, **_kwargs):
            raise RuntimeError("PostgreSQL rollback test")

        monkeypatch.setattr(session, "flush", fail_flush)
        with pytest.raises(RuntimeError, match="rollback test"):
            service.cancel_invoice(
                company_id=company.company_id,
                fiscal_year=FY26,
                open_item_id=rollback_item_id,
                booking_date=date(2026, 6, 16),
                reason="Rollbacktest",
                confirmed=True,
            )
        monkeypatch.setattr(session, "flush", original_flush)
        assert session.query(RechnungsOPStorno).filter_by(
            receivable_open_item_id=str(rollback_item_id)
        ).count() == 0
        assert session.query(Buchung).filter(
            Buchung.reversal_of_booking_id == str(rollback_invoice.booking_id)
        ).count() == 0
    finally:
        if session is not None:
            session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def _cancellation_service(session: Session) -> OpenItemInvoiceCancellationService:
    return OpenItemInvoiceCancellationService(
        OpenItemInvoiceCancellationRepository(
            session=session,
            booking_repository=BookingRepository(session),
        )
    )


def test_payment_assessment_nets_multiple_payments_and_correction_roles():
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, _payables, payments, _credits, _offsets, corrections,
        _overview,
    ) = _environment()
    try:
        source = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-SOURCE", date_value=date(2026, 3, 1),
        )
        target = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-TARGET", date_value=date(2026, 3, 1),
        )
        source_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=source.invoice_id
        )
        target_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=target.invoice_id
        )
        first = _post_payment(
            payments, company, partner, source_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="50.00", booking_date=date(2026, 3, 3),
        )
        _post_payment(
            payments, company, partner, source_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="20.00", booking_date=date(2026, 3, 5),
        )
        event_id = UUID(
            session.query(RechnungsOPZahlungsereignis.event_id)
            .filter_by(payment_id=str(first.payment_id)).scalar()
        )
        corrections.correct(
            company_id=company.company_id, fiscal_year=FY26,
            original_event_id=event_id, target_open_item_id=target_id,
            amount=Decimal("10.00"), correction_date=date(2026, 3, 8),
            booking_date=date(2026, 3, 8), reason="Fehlzuordnung", confirmed=True,
        )

        service = _cancellation_service(session)
        source_assessment = service.assess_payment_history(
            company_id=company.company_id, fiscal_year=FY26,
            open_item_id=source_id, proposed_booking_date=date(2026, 3, 8),
        )
        assert source_assessment.payment_event_amount == Decimal("70.00")
        assert source_assessment.correction_delta == Decimal("-10.00")
        assert source_assessment.effective_payment_amount == Decimal("60.00")
        assert source_assessment.open_amount == Decimal("59.00")
        assert source_assessment.latest_payment_booking_date == date(2026, 3, 5)
        assert source_assessment.latest_correction_booking_date == date(2026, 3, 8)
        assert source_assessment.latest_required_booking_date == date(2026, 3, 8)
        assert source_assessment.payment_event_count == 2
        assert source_assessment.correction_count == 1

        target_assessment = service.assess_payment_history(
            company_id=company.company_id, fiscal_year=FY26,
            open_item_id=target_id, proposed_booking_date=date(2026, 3, 8),
        )
        assert target_assessment.payment_event_amount == Decimal("0.00")
        assert target_assessment.correction_delta == Decimal("10.00")
        assert target_assessment.effective_payment_amount == Decimal("10.00")
        assert target_assessment.open_amount == Decimal("109.00")
        with pytest.raises(ValueError, match="nicht vor dem spätesten"):
            service.assess_payment_history(
                company_id=company.company_id, fiscal_year=FY26,
                open_item_id=source_id, proposed_booking_date=date(2026, 3, 7),
            )
        source_release = session.query(
            Zahlungszuordnungskorrekturereignis
        ).filter_by(event_role="SOURCE_RELEASE").one()
        source_release.amount_delta = Decimal("-9.00")
        session.commit()
        with pytest.raises(ValueError, match="sind widersprüchlich"):
            service.assess_payment_history(
                company_id=company.company_id, fiscal_year=FY26,
                open_item_id=source_id, proposed_booking_date=date(2026, 3, 8),
            )
    finally:
        session.close()
        engine.dispose()


def test_payment_assessment_nets_repeated_partial_corrections_once():
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, _payables, payments, _credits, _offsets, corrections,
        _overview,
    ) = _environment()
    try:
        source = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-REPEATED-SOURCE", date_value=date(2026, 3, 1),
        )
        target = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-REPEATED-TARGET", date_value=date(2026, 3, 1),
        )
        source_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=source.invoice_id
        )
        target_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=target.invoice_id
        )
        payment = _post_payment(
            payments, company, partner, source_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="50.00", booking_date=date(2026, 3, 3),
        )
        event_id = UUID(
            session.query(RechnungsOPZahlungsereignis.event_id)
            .filter_by(payment_id=str(payment.payment_id)).scalar()
        )
        for amount, event_date in (
            (Decimal("10.00"), date(2026, 3, 5)),
            (Decimal("15.00"), date(2026, 3, 7)),
        ):
            corrections.correct(
                company_id=company.company_id,
                fiscal_year=FY26,
                original_event_id=event_id,
                target_open_item_id=target_id,
                amount=amount,
                correction_date=event_date,
                booking_date=event_date,
                reason="Teilkorrektur der Zahlungszuordnung",
                confirmed=True,
            )

        source_release_total = session.query(
            func.sum(Zahlungszuordnungskorrekturereignis.amount_delta)
        ).filter_by(
            receivable_open_item_id=str(source_id), event_role="SOURCE_RELEASE"
        ).scalar()
        target_apply_total = session.query(
            func.sum(Zahlungszuordnungskorrekturereignis.amount_delta)
        ).filter_by(
            receivable_open_item_id=str(target_id), event_role="TARGET_APPLY"
        ).scalar()
        assert source_release_total == Decimal("-25.00")
        assert target_apply_total == Decimal("25.00")

        service = _cancellation_service(session)
        source_assessment = service.assess_payment_history(
            company_id=company.company_id,
            fiscal_year=FY26,
            open_item_id=source_id,
            proposed_booking_date=date(2026, 3, 7),
        )
        target_assessment = service.assess_payment_history(
            company_id=company.company_id,
            fiscal_year=FY26,
            open_item_id=target_id,
            proposed_booking_date=date(2026, 3, 7),
        )
        assert source_assessment.payment_event_amount == Decimal("50.00")
        assert source_assessment.correction_delta == Decimal("-25.00")
        assert source_assessment.effective_payment_amount == Decimal("25.00")
        assert source_assessment.open_amount == Decimal("94.00")
        assert source_assessment.correction_count == 2
        assert target_assessment.payment_event_amount == Decimal("0.00")
        assert target_assessment.correction_delta == Decimal("25.00")
        assert target_assessment.effective_payment_amount == Decimal("25.00")
        assert target_assessment.open_amount == Decimal("94.00")
        assert target_assessment.correction_count == 2
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("supplier", (False, True), ids=("customer", "supplier"))
def test_payment_assessment_supports_fully_paid_customer_and_supplier_invoices(supplier):
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, payables, payments, _credits, _offsets, _corrections,
        _overview,
    ) = _environment()
    try:
        invoice = _invoice(
            payables if supplier else receivables,
            company, partner, year=FY26,
            number="AP-ASSESS-FULL" if supplier else "AR-ASSESS-FULL",
            date_value=date(2026, 3, 1), supplier=supplier,
        )
        op_model = VerbindlichkeitsOP if supplier else ForderungsOP
        open_item_id = _open_id(
            session, op_model, foreign_key="invoice_id", foreign_id=invoice.invoice_id
        )
        direction = (
            PaymentDirection.SUPPLIER_PAYMENT
            if supplier
            else PaymentDirection.CUSTOMER_RECEIPT
        )
        _post_payment(
            payments, company, partner, open_item_id,
            direction=direction, amount="70.00", booking_date=date(2026, 3, 3),
        )
        payments.post_payment(
            company_id=company.company_id,
            fiscal_year=FY26,
            partner_id=partner.partner_id,
            open_item_id=open_item_id,
            direction=direction,
            amount=Decimal("49.00"),
            payment_date=date(2026, 3, 1),
            booking_date=date(2026, 3, 5),
            cash_bank_account_number="1000",
        )
        assessment = _cancellation_service(session).assess_payment_history(
            company_id=company.company_id, fiscal_year=FY26,
            open_item_id=open_item_id, proposed_booking_date=date(2026, 3, 5),
        )
        assert assessment.invoice_amount == Decimal("119.00")
        assert assessment.effective_payment_amount == Decimal("119.00")
        assert assessment.open_amount == Decimal("0.00")
        assert assessment.payment_event_count == 2
        assert assessment.latest_required_booking_date == date(2026, 3, 5)
        with pytest.raises(ValueError, match="nicht vor dem spätesten"):
            _cancellation_service(session).assess_payment_history(
                company_id=company.company_id, fiscal_year=FY26,
                open_item_id=open_item_id, proposed_booking_date=date(2026, 3, 4),
            )
    finally:
        session.close()
        engine.dispose()


def test_payment_assessment_rejects_unknown_correction_booking_date():
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, _payables, payments, _credits, _offsets, corrections,
        _overview,
    ) = _environment()
    try:
        source = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-NULL", date_value=date(2026, 3, 1),
        )
        target = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-NULL-TARGET", date_value=date(2026, 3, 1),
        )
        source_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=source.invoice_id
        )
        target_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=target.invoice_id
        )
        payment = _post_payment(
            payments, company, partner, source_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="10.00", booking_date=date(2026, 3, 3),
        )
        event_id = UUID(
            session.query(RechnungsOPZahlungsereignis.event_id)
            .filter_by(payment_id=str(payment.payment_id)).scalar()
        )
        corrections.correct(
            company_id=company.company_id, fiscal_year=FY26,
            original_event_id=event_id, target_open_item_id=target_id,
            amount=Decimal("2.00"), correction_date=date(2026, 3, 5),
            booking_date=date(2026, 3, 5), reason="Korrekturdatum-Test", confirmed=True,
        )
        correction = session.query(Zahlungszuordnungskorrektur).one()
        assert correction.booking_id is None
        correction.booking_date = None
        session.commit()
        with pytest.raises(ValueError, match="kein gespeichertes Buchungsdatum"):
            _cancellation_service(session).assess_payment_history(
                company_id=company.company_id, fiscal_year=FY26,
                open_item_id=source_id, proposed_booking_date=date(2026, 3, 5),
            )
    finally:
        session.close()
        engine.dispose()


def test_payment_assessment_rejects_invoice_with_credit_offset_history():
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, _payables, _payments, credits, offsets, _corrections,
        _overview,
    ) = _environment()
    try:
        invoice = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-ASSESS-OFFSET", date_value=date(2026, 3, 1),
        )
        open_item_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=invoice.invoice_id
        )
        credit = _credit(credits, company, partner, number="CN-ASSESS", amount="5.00")
        credit_id = _open_id(
            session, GuthabenOP, foreign_key="credit_note_id", foreign_id=credit.credit_note_id
        )
        _offset(
            offsets, company, partner, invoice_id=open_item_id,
            credit_id=credit_id, amount="1.00", direction=OffsetDirection.CUSTOMER,
        )
        with pytest.raises(ValueError, match="Verrechnungshistorie"):
            _cancellation_service(session).assess_payment_history(
                company_id=company.company_id, fiscal_year=FY26,
                open_item_id=open_item_id, proposed_booking_date=date(2026, 4, 12),
            )
    finally:
        session.close()
        engine.dispose()


def test_stornoed_invoice_rejects_later_payment_offset_and_correction():
    (
        engine, session, company, _other_company, partner, _other_partner,
        receivables, _payables, payments, credits, offsets, corrections,
        _overview,
    ) = _environment()
    try:
        invoice = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-STORNO-GUARD", date_value=date(2026, 3, 1),
        )
        open_item_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=invoice.invoice_id
        )
        storno_service = _cancellation_service(session)
        storno_service.cancel_invoice(
            company_id=company.company_id, fiscal_year=FY26,
            open_item_id=open_item_id, booking_date=date(2026, 3, 10),
            reason="4D-2-Schutztest", confirmed=True,
        )
        counts_before = (
            session.query(Buchung).count(),
            session.query(Zahlung).count(),
            session.query(OPGuthabenverrechnung).count(),
        )
        with pytest.raises(ValueError, match="vollständig ausgeglichen"):
            _post_payment(
                payments, company, partner, open_item_id,
                direction=PaymentDirection.CUSTOMER_RECEIPT,
                amount="1.00", booking_date=date(2026, 3, 11),
            )
        credit = _credit(credits, company, partner, number="CN-GUARD", amount="1.00")
        credit_id = _open_id(
            session, GuthabenOP, foreign_key="credit_note_id", foreign_id=credit.credit_note_id
        )
        with pytest.raises(ValueError, match="storniert"):
            _offset(
                offsets, company, partner, invoice_id=open_item_id,
                credit_id=credit_id, amount="1.00", direction=OffsetDirection.CUSTOMER,
            )
        with pytest.raises(ValueError, match="storniert"):
            OpenItemPaymentRepository(session).ensure_not_cancelled(
                open_item_id=open_item_id,
                direction=PaymentDirection.CUSTOMER_RECEIPT,
            )
        assert (
            session.query(Buchung).count(),
            session.query(Zahlung).count(),
            session.query(OPGuthabenverrechnung).count(),
        ) == (counts_before[0] + 1, counts_before[1], counts_before[2])

        # Für eine künftige bezahlte Stornostufe liegt eine Zahlungszuordnung
        # vor; der Repository-Guard sperrt danach auch deren Korrektur.
        paid_invoice = _invoice(
            receivables, company, partner, year=FY26,
            number="AR-STORNO-CORRECTION-GUARD", date_value=date(2026, 3, 1),
        )
        paid_id = _open_id(
            session, ForderungsOP, foreign_key="invoice_id", foreign_id=paid_invoice.invoice_id
        )
        payment = _post_payment(
            payments, company, partner, paid_id,
            direction=PaymentDirection.CUSTOMER_RECEIPT,
            amount="10.00", booking_date=date(2026, 3, 4),
        )
        mandate = session.query(Mandant).filter_by(
            company_id=str(company.company_id)
        ).one()
        session.add(RechnungsOPStorno(
            storno_id=str(uuid4()),
            mandant_id=mandate.id,
            partner_id=str(partner.partner_id),
            receivable_invoice_id=str(paid_invoice.invoice_id),
            payable_invoice_id=None,
            receivable_open_item_id=str(paid_id),
            payable_open_item_id=None,
            booking_id=str(paid_invoice.booking_id),
            credit_booking_id=None,
            amount=Decimal("119.00"),
            closed_open_amount=Decimal("109.00"),
            recorded_at=datetime.now(timezone.utc),
            reason="Guard-Fixture für später bezahltes Storno",
        ))
        session.commit()
        event_id = UUID(
            session.query(RechnungsOPZahlungsereignis.event_id)
            .filter_by(payment_id=str(payment.payment_id)).scalar()
        )
        correction_counts = (
            session.query(Buchung).count(),
            session.query(Zahlungszuordnungskorrektur).count(),
            session.query(Zahlungszuordnungskorrekturereignis).count(),
        )
        with pytest.raises(ValueError, match="storniert"):
            corrections.correct(
                company_id=company.company_id, fiscal_year=FY26,
                original_event_id=event_id, target_open_item_id=open_item_id,
                amount=Decimal("1.00"), correction_date=date(2026, 3, 12),
                booking_date=date(2026, 3, 12), reason="Nachstornokorrektur",
                confirmed=True,
            )
        assert (
            session.query(Buchung).count(),
            session.query(Zahlungszuordnungskorrektur).count(),
            session.query(Zahlungszuordnungskorrekturereignis).count(),
        ) == correction_counts
    finally:
        session.close()
        engine.dispose()
