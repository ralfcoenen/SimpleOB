"""Tests für die Persistenz von Buchungen."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear


def test_adds_and_loads_booking() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository = BookingRepository(
            session
        )

        booking = Booking(
            booking_id=uuid4(),
            booking_date=date(2026, 8, 8),
            voucher_no="RE-001",
            description="Büromaterial",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("500.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("500.00"),
                ),
            ),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        loaded_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert loaded_bookings == (booking,)

def test_preserves_closing_booking_type() -> None:
    """Der Buchungstyp bleibt beim Datenbank-Roundtrip erhalten."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository = BookingRepository(
            session
        )

        booking = Booking(
            booking_date=date(2026, 12, 31),
            description="Abschluss des GuV-Kontos",
            booking_type=BookingType.CLOSING,
            lines=(
                BookingLine(
                    account_number="8990",
                    side=EntrySide.DEBIT,
                    amount=Decimal("4500.00"),
                ),
                BookingLine(
                    account_number="8020",
                    side=EntrySide.CREDIT,
                    amount=Decimal("4500.00"),
                ),
            ),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        loaded_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert len(loaded_bookings) == 1
    assert (
        loaded_bookings[0].booking_type
        is BookingType.CLOSING
    )
    assert loaded_bookings[0] == booking

def test_preserves_reversal_booking_reference() -> None:
    """Die Referenz einer Stornobuchung bleibt beim Roundtrip erhalten."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    original_booking = Booking(
        booking_date=date(2026, 6, 1),
        voucher_no="RE-001",
        description="Ausgangsrechnung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.CREDIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    reversal_booking = Booking(
        booking_date=date(2026, 6, 2),
        description="Storno zu Buchung RE-001",
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=(
            original_booking.booking_id
        ),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=original_booking,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=reversal_booking,
        )

        loaded_booking = booking_repository.get(
            reversal_booking.booking_id
        )

    assert loaded_booking == reversal_booking
    assert (
        loaded_booking.booking_type
        is BookingType.REVERSAL
    )
    assert (
        loaded_booking.reversal_of_booking_id
        == original_booking.booking_id
    )
    assert loaded_booking.lines == (
        BookingLine(
            account_number="1200",
            side=EntrySide.CREDIT,
            amount=Decimal("119.00"),
        ),
        BookingLine(
            account_number="8400",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        ),
        BookingLine(
            account_number="1776",
            side=EntrySide.DEBIT,
            amount=Decimal("19.00"),
        ),
    )

def test_rejects_second_reversal_for_same_booking() -> None:
    """Eine reguläre Buchung darf nur einmal storniert werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    original_booking = Booking(
        booking_date=date(2026, 6, 1),
        voucher_no="RE-001",
        description="Ausgangsrechnung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.CREDIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    first_reversal = Booking(
        booking_date=date(2026, 6, 2),
        description="Erstes Storno",
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=(
            original_booking.booking_id
        ),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    second_reversal = Booking(
        booking_date=date(2026, 6, 3),
        description="Zweites Storno",
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=(
            original_booking.booking_id
        ),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=original_booking,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=first_reversal,
        )

        with pytest.raises(
            ValueError,
            match="bereits storniert",
        ):
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=second_reversal,
            )

def test_rejects_reversal_for_missing_original_booking() -> None:
    """Eine Stornobuchung benötigt eine vorhandene Originalbuchung."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    reversal_booking = Booking(
        booking_date=date(2026, 6, 2),
        description="Storno ohne Original",
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=uuid4(),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="nicht vorhanden",
        ):
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=reversal_booking,
            )

def test_rejects_duplicate_booking_id() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        repository = BookingRepository(
            session
        )

        booking_id = uuid4()

        first_booking = Booking(
            booking_id=booking_id,
            booking_date=date(2026, 8, 8),
            description="Erste Buchung",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("100.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
            ),
        )

        duplicate_booking = Booking(
            booking_id=booking_id,
            booking_date=date(2026, 8, 9),
            description="Doppelte Buchungs-ID",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("200.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("200.00"),
                ),
            ),
        )

        repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=first_booking,
        )

        with pytest.raises(
            ValueError,
            match="Buchung ist bereits vorhanden",
        ):
            repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=duplicate_booking,
            )

def test_rejects_booking_outside_fiscal_year() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        repository = BookingRepository(
            session
        )

        booking = Booking(
            booking_date=date(2027, 1, 1),
            description="Buchung außerhalb des Geschäftsjahres",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("100.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
            ),
        )

        with pytest.raises(
            ValueError,
            match="Buchungsdatum liegt außerhalb",
        ):
            repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
            )

def test_separates_bookings_by_fiscal_year() -> None:
    """Buchungen verschiedener Geschäftsjahre bleiben getrennt."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year_2026 = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    fiscal_year_2027 = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    booking_2026 = Booking(
        booking_date=date(2026, 12, 15),
        voucher_no="RE-2026-001",
        description="Buchung 2026",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    booking_2027 = Booking(
        booking_date=date(2027, 1, 15),
        voucher_no="RE-2027-001",
        description="Buchung 2027",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("200.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("200.00"),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year_2026,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year_2027,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year_2026,
            booking=booking_2026,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year_2027,
            booking=booking_2027,
        )

        loaded_2026 = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year_2026,
            )
        )

        loaded_2027 = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year_2027,
            )
        )

    assert loaded_2026 == (
        booking_2026,
    )

    assert loaded_2027 == (
        booking_2027,
    )

    assert booking_2027 not in loaded_2026
    assert booking_2026 not in loaded_2027

def test_rejects_booking_for_closed_fiscal_year() -> None:
    """In ein abgeschlossenes Geschäftsjahr darf nicht gebucht werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        company_repository.close_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking = Booking(
            booking_date=date(2026, 12, 31),
            description="Buchung nach Abschluss",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("100.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
            ),
        )

        with pytest.raises(
            ValueError,
            match="Geschäftsjahr ist abgeschlossen",
        ):
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
            )

def test_add_can_defer_commit() -> None:
    """Eine Buchung kann ohne sofortigen Commit vorgemerkt werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    booking = Booking(
        booking_date=date(2026, 8, 8),
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
            commit=False,
        )

        session.rollback()

    with Session() as session:
        booking_repository = BookingRepository(
            session
        )

        loaded = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert loaded == ()
