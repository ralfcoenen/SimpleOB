"""Tests für Ergebnisverwendungsbuchungen."""

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
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.profit_appropriation_posting import (
    ProfitAppropriationPosting,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


def _source_fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _target_fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )


def _distribution_booking(
    *,
    amount: Decimal,
    booking_date: date,
) -> Booking:
    return Booking(
        booking_date=booking_date,
        description="Ergebnisverwendung: Ausschüttung",
        lines=(
            BookingLine(
                account_number="2970",
                side=EntrySide.DEBIT,
                amount=amount,
            ),
            BookingLine(
                account_number="0755",
                side=EntrySide.CREDIT,
                amount=amount,
            ),
        ),
    )


def test_adds_and_loads_profit_appropriation_posting() -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()

    booking = _distribution_booking(
        amount=Decimal("5000.00"),
        booking_date=date(2027, 3, 15),
    )

    posting = ProfitAppropriationPosting(
        source_fiscal_year_end=(
            source_fiscal_year.end_date
        ),
        posting_date=booking.booking_date,
        amount=Decimal("5000.00"),
        booking_id=booking.booking_id,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )
        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
            booking=booking,
        )

        posting_repository.add(
            company_id=company.company_id,
            posting=posting,
            booking_line_position=0,
        )

        loaded = posting_repository.get(
            posting.posting_id
        )

        postings = (
            posting_repository.list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

        source_year_postings = (
            posting_repository.list_for_posting_fiscal_year(
                company_id=company.company_id,
                fiscal_year=source_fiscal_year,
            )
        )

        target_year_postings = (
            posting_repository.list_for_posting_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
        )

    assert loaded == posting
    assert postings == (posting,)
    assert loaded.booking_id == booking.booking_id
    assert (
        loaded.source_fiscal_year_end
        == date(2026, 12, 31)
    )
    assert source_year_postings == ()
    assert target_year_postings == (posting,)


def test_allows_same_posting_type_with_different_bookings() -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()

    first_booking = _distribution_booking(
        amount=Decimal("5000.00"),
        booking_date=date(2027, 3, 15),
    )
    second_booking = _distribution_booking(
        amount=Decimal("5000.00"),
        booking_date=date(2027, 3, 20),
    )

    first_posting = ProfitAppropriationPosting(
        source_fiscal_year_end=(
            source_fiscal_year.end_date
        ),
        posting_date=first_booking.booking_date,
        amount=Decimal("5000.00"),
        booking_id=first_booking.booking_id,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    second_posting = ProfitAppropriationPosting(
        source_fiscal_year_end=(
            source_fiscal_year.end_date
        ),
        posting_date=second_booking.booking_date,
        amount=Decimal("5000.00"),
        booking_id=second_booking.booking_id,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )
        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
            booking=first_booking,
        )
        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
            booking=second_booking,
        )

        posting_repository.add(
            company_id=company.company_id,
            posting=first_posting,
            booking_line_position=0,
        )
        posting_repository.add(
            company_id=company.company_id,
            posting=second_posting,
            booking_line_position=0,
        )

        postings = (
            posting_repository.list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=(
                    source_fiscal_year.end_date
                ),
            )
        )

    assert postings == (
        first_posting,
        second_posting,
    )


def test_rejects_reusing_booking_line() -> None:
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
    source_fiscal_year = _source_fiscal_year()
    target_fiscal_year = _target_fiscal_year()

    booking = _distribution_booking(
        amount=Decimal("5000.00"),
        booking_date=date(2027, 3, 15),
    )

    first_posting = ProfitAppropriationPosting(
        source_fiscal_year_end=(
            source_fiscal_year.end_date
        ),
        posting_date=booking.booking_date,
        amount=Decimal("5000.00"),
        booking_id=booking.booking_id,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    second_posting = ProfitAppropriationPosting(
        source_fiscal_year_end=(
            source_fiscal_year.end_date
        ),
        posting_date=booking.booking_date,
        amount=Decimal("5000.00"),
        booking_id=booking.booking_id,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        posting_repository = (
            ProfitAppropriationPostingRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )
        company_repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
            booking=booking,
        )

        posting_repository.add(
            company_id=company.company_id,
            posting=first_posting,
            booking_line_position=0,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Buchungszeile ist bereits einer "
                "Ergebnisverwendungsbuchung zugeordnet"
            ),
        ):
            posting_repository.add(
                company_id=company.company_id,
                posting=second_posting,
                booking_line_position=0,
            )
