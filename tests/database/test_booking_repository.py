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
    