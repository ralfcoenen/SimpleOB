"""Integrationstests für die aktuelle OP-Übersicht."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

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
    Buchungszeile,
    ForderungsOP,
    GuthabenOP,
    GuthabenOPEreignis,
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
from simpleob.database.open_item_overview_repository import OpenItemOverviewRepository
from simpleob.database.open_item_payment_repository import OpenItemPaymentRepository
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


def _environment():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
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
    )
    return tuple(session.query(model).count() for model in models)
