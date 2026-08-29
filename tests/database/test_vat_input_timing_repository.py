"""Tests für die Persistenz der Vorsteuer-Zeitzuordnung."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.models import Base
from openbilanz.database.vat_input_timing_repository import (
    VatInputTimingRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_input_timing import VatInputTiming


def _booking(
    *,
    booking_date: date,
) -> Booking:
    return Booking(
        booking_date=booking_date,
        voucher_no="ER-001",
        description="Eingangsrechnung",
        lines=(
            BookingLine(
                account_number="4930",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1576",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
            BookingLine(
                account_number="1600",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
        ),
    )


def test_saves_and_loads_vat_input_timing() -> None:
    """Eine Vorsteuer-Zeitzuordnung wird vollständig gespeichert."""

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

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking = _booking(
            booking_date=date(2026, 4, 7),
        )

        BookingRepository(session).add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        repository = VatInputTimingRepository(
            session
        )

        timing = VatInputTiming(
            booking_id=booking.booking_id,
            service_date=date(2026, 3, 28),
            invoice_received_date=date(
                2026,
                4,
                4,
            ),
        )

        repository.add(
            timing
        )

        loaded = repository.get_for_booking(
            booking.booking_id
        )

    assert loaded == timing


def test_lists_vat_input_timing_by_deductible_date() -> None:
    """Der Zeitraum richtet sich nach dem späteren der beiden Daten."""

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

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )

        company_repository.add(
            company
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        march_booking = _booking(
            booking_date=date(2026, 3, 31),
        )

        april_booking = _booking(
            booking_date=date(2026, 4, 5),
        )

        booking_repository = BookingRepository(
            session
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=march_booking,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=april_booking,
        )

        repository = VatInputTimingRepository(
            session
        )

        march_timing = VatInputTiming(
            booking_id=march_booking.booking_id,
            service_date=date(2026, 3, 20),
            invoice_received_date=date(
                2026,
                3,
                25,
            ),
        )

        april_timing = VatInputTiming(
            booking_id=april_booking.booking_id,
            service_date=date(2026, 3, 28),
            invoice_received_date=date(
                2026,
                4,
                4,
            ),
        )

        repository.add(
            march_timing
        )

        repository.add(
            april_timing
        )

        result = (
            repository
            .list_for_company_in_date_range(
                company_id=company.company_id,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 30),
            )
        )

    assert result == (
        april_timing,
    )


def test_returns_none_for_unknown_booking() -> None:
    """Für eine unbekannte Buchung gibt es keine Zeitzuordnung."""

    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = VatInputTimingRepository(
            session
        )

        loaded = repository.get_for_booking(
            uuid4()
        )

    assert loaded is None
