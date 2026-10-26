"""Schützt OP-Ursprungsbuchungen vor isoliertem Journalstorno."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.database.models import (
    Ausgangsrechnung,
    Eingangsrechnung,
    ForderungsOP,
    GuthabenOP,
    GuthabenOPEreignis,
    Gutschrift,
    Mandant,
    OPGuthabenverrechnung,
    RechnungsOPVerrechnungsereignis,
    RechnungsOPZahlungsereignis,
    VerbindlichkeitsOP,
    Wirtschaftsjahr,
    Zahlung,
)
from simpleob.database.models import (
    Buchung as BookingModel,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus

FY = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
AMOUNT = Decimal("119.00")
STORNO_ERROR = "spezielle OP-Stornierung erforderlich"


def _environment():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    company = Company(uuid4(), "OP-Storno Test UG")
    CompanyRepository(session).add(company)
    CompanyRepository(session).add_fiscal_year(company.company_id, FY)
    mandate = session.query(Mandant).filter_by(
        company_id=str(company.company_id)
    ).one()
    session.query(Wirtschaftsjahr).one().status = FiscalYearStatus.OPEN.value
    partner = BusinessPartner(
        company_id=company.company_id,
        name="Kunde und Lieferant GmbH",
        is_customer=True,
        is_supplier=True,
    )
    BusinessPartnerRepository(session).add(partner)
    session.commit()
    return engine, session, company, mandate, partner


@pytest.mark.parametrize(
    ("document_kind", "document_model", "open_item_model"),
    [
        ("Kundenrechnung", Ausgangsrechnung, ForderungsOP),
        ("Lieferantenrechnung", Eingangsrechnung, VerbindlichkeitsOP),
        ("Kundengutschrift", Gutschrift, GuthabenOP),
        ("Lieferantengutschrift", Gutschrift, GuthabenOP),
    ],
)
def test_repository_rejects_reversal_of_all_open_item_source_bookings(
    document_kind, document_model, open_item_model
):
    engine, session, company, mandate, partner = _environment()
    try:
        repository = BookingRepository(session)
        original = Booking(
            booking_date=date(2026, 3, 2),
            description=f"Ursprung {document_kind}",
            lines=(
                BookingLine("1200", EntrySide.DEBIT, AMOUNT),
                BookingLine("8400", EntrySide.CREDIT, AMOUNT),
            ),
        )
        repository.add(
            company_id=company.company_id,
            fiscal_year=FY,
            booking=original,
        )

        if document_model is Ausgangsrechnung:
            document = document_model(
                invoice_id=str(uuid4()),
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                invoice_number="AR-1",
                invoice_date=date(2026, 3, 2),
                due_date=date(2026, 4, 1),
                gross_amount=AMOUNT,
                booking_id=str(original.booking_id),
            )
            open_item = open_item_model(
                open_item_id=str(uuid4()),
                invoice_id=document.invoice_id,
                amount=AMOUNT,
            )
        elif document_model is Eingangsrechnung:
            document = document_model(
                invoice_id=str(uuid4()),
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                invoice_number="ER-1",
                invoice_date=date(2026, 3, 2),
                due_date=date(2026, 4, 1),
                gross_amount=AMOUNT,
                booking_id=str(original.booking_id),
            )
            open_item = open_item_model(
                open_item_id=str(uuid4()),
                invoice_id=document.invoice_id,
                amount=AMOUNT,
            )
        else:
            document = document_model(
                credit_note_id=str(uuid4()),
                mandant_id=mandate.id,
                partner_id=str(partner.partner_id),
                credit_note_kind=(
                    "CUSTOMER" if document_kind == "Kundengutschrift" else "SUPPLIER"
                ),
                note_number="GS-1",
                note_date=date(2026, 3, 2),
                booking_id=str(original.booking_id),
            )
            open_item = open_item_model(
                open_item_id=str(uuid4()),
                credit_note_id=document.credit_note_id,
                amount=AMOUNT,
            )

        session.add(document)
        session.flush()
        session.add(open_item)
        session.commit()
        reversal = Booking(
            booking_date=date(2026, 3, 3),
            description=f"Storno zu {document_kind}",
            booking_type=BookingType.REVERSAL,
            reversal_of_booking_id=original.booking_id,
            lines=(
                BookingLine("1200", EntrySide.CREDIT, AMOUNT),
                BookingLine("8400", EntrySide.DEBIT, AMOUNT),
            ),
        )

        with pytest.raises(ValueError, match=STORNO_ERROR):
            repository.add(
                company_id=company.company_id,
                fiscal_year=FY,
                booking=reversal,
            )

        session.expire_all()
        assert session.query(BookingModel).count() == 1
        assert session.query(document_model).count() == 1
        stored_open_item = session.query(open_item_model).one()
        assert stored_open_item.amount == AMOUNT
        assert session.query(Zahlung).count() == 0
        assert session.query(RechnungsOPZahlungsereignis).count() == 0
        assert session.query(OPGuthabenverrechnung).count() == 0
        assert session.query(RechnungsOPVerrechnungsereignis).count() == 0
        assert session.query(GuthabenOPEreignis).count() == 0
    finally:
        session.close()
        engine.dispose()


def test_ordinary_booking_can_still_be_reversed():
    engine, session, company, _mandate, _partner = _environment()
    try:
        repository = BookingRepository(session)
        original = Booking(
            booking_date=date(2026, 3, 2),
            description="Gewöhnliche Buchung",
            lines=(
                BookingLine("4980", EntrySide.DEBIT, AMOUNT),
                BookingLine("1200", EntrySide.CREDIT, AMOUNT),
            ),
        )
        repository.add(
            company_id=company.company_id,
            fiscal_year=FY,
            booking=original,
        )
        reversal = Booking(
            booking_date=date(2026, 3, 3),
            description="Storno gewöhnliche Buchung",
            booking_type=BookingType.REVERSAL,
            reversal_of_booking_id=original.booking_id,
            lines=(
                BookingLine("4980", EntrySide.CREDIT, AMOUNT),
                BookingLine("1200", EntrySide.DEBIT, AMOUNT),
            ),
        )

        repository.add(
            company_id=company.company_id,
            fiscal_year=FY,
            booking=reversal,
        )

        assert session.query(BookingModel).count() == 2
    finally:
        session.close()
        engine.dispose()
