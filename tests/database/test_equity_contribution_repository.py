"""Tests für die Persistenz von BVV-Einlagen."""

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
from openbilanz.database.equity_contribution_repository import (
    EquityContributionRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.equity_contribution_reference import (
    EquityContributionReference,
)
from openbilanz.domain.fiscal_year import FiscalYear


def _fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _contribution_booking() -> Booking:
    return Booking(
        booking_date=date(2026, 3, 15),
        description="Einzahlung Stammkapital",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("10000.00"),
            ),
            BookingLine(
                account_number="0800",
                side=EntrySide.CREDIT,
                amount=Decimal("10000.00"),
            ),
        ),
    )


def test_adds_and_lists_equity_contribution_reference() -> None:
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
    fiscal_year = _fiscal_year()
    booking = _contribution_booking()

    reference = EquityContributionReference(
        booking_id=booking.booking_id,
        booking_line_position=1,
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        contribution_repository = (
            EquityContributionRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        contribution_repository.add(
            company_id=company.company_id,
            reference=reference,
        )

        loaded = (
            contribution_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert loaded == (reference,)


def test_allows_multiple_contribution_lines_in_one_booking() -> None:
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
    fiscal_year = _fiscal_year()

    booking = Booking(
        booking_date=date(2026, 3, 15),
        description="Eigenkapitalzuführung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("7000.00"),
            ),
            BookingLine(
                account_number="0800",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="0810",
                side=EntrySide.CREDIT,
                amount=Decimal("5000.00"),
            ),
        ),
    )

    first_reference = EquityContributionReference(
        booking_id=booking.booking_id,
        booking_line_position=1,
    )
    second_reference = EquityContributionReference(
        booking_id=booking.booking_id,
        booking_line_position=2,
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        contribution_repository = (
            EquityContributionRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        contribution_repository.add(
            company_id=company.company_id,
            reference=first_reference,
        )
        contribution_repository.add(
            company_id=company.company_id,
            reference=second_reference,
        )

        loaded = (
            contribution_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert loaded == (
        first_reference,
        second_reference,
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
    fiscal_year = _fiscal_year()
    booking = _contribution_booking()

    reference = EquityContributionReference(
        booking_id=booking.booking_id,
        booking_line_position=1,
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        contribution_repository = (
            EquityContributionRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        contribution_repository.add(
            company_id=company.company_id,
            reference=reference,
        )

        with pytest.raises(
            ValueError,
            match=(
                "Buchungszeile ist bereits als "
                "BVV-Einlage gekennzeichnet"
            ),
        ):
            contribution_repository.add(
                company_id=company.company_id,
                reference=reference,
            )


def test_rejects_booking_line_from_other_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    first_company = Company(
        company_id=uuid4(),
        name="Erste UG",
    )
    second_company = Company(
        company_id=uuid4(),
        name="Zweite UG",
    )
    fiscal_year = _fiscal_year()
    booking = _contribution_booking()

    reference = EquityContributionReference(
        booking_id=booking.booking_id,
        booking_line_position=1,
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        contribution_repository = (
            EquityContributionRepository(
                session
            )
        )

        company_repository.add(
            first_company
        )
        company_repository.add(
            second_company
        )

        company_repository.add_fiscal_year(
            first_company.company_id,
            fiscal_year,
        )
        company_repository.add_fiscal_year(
            second_company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=first_company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        with pytest.raises(
            ValueError,
            match="Die Buchung ist nicht vorhanden",
        ):
            contribution_repository.add(
                company_id=second_company.company_id,
                reference=reference,
            )
