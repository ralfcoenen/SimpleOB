"""Tests für umsatzsteuerliche Buchungsdetails."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.database.vat_booking_detail_repository import (
    VatBookingDetailRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_booking_direction import (
    VatBookingDirection,
)


def test_saves_and_loads_vat_booking_details() -> None:
    """Mehrere USt-Details einer Buchung können gespeichert werden."""

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

        booking = Booking(
            booking_date=date(2026, 8, 1),
            lines=(
                BookingLine(
                    account_number="1400",
                    side=EntrySide.DEBIT,
                    amount=Decimal("189.00"),
                ),
                BookingLine(
                    account_number="8300",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
                BookingLine(
                    account_number="1776",
                    side=EntrySide.CREDIT,
                    amount=Decimal("19.00"),
                ),
                BookingLine(
                    account_number="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("65.42"),
                ),
                BookingLine(
                    account_number="1771",
                    side=EntrySide.CREDIT,
                    amount=Decimal("4.58"),
                ),
            ),
        )

        BookingRepository(session).add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        repository = VatBookingDetailRepository(
            session
        )

        details = (
            VatBookingDetail(
                booking_id=booking.booking_id,
                account_number="8300",
                net_amount=Decimal("100.00"),
                tax_amount=Decimal("19.00"),
                tax_rate=19,
                direction=VatBookingDirection.OUTPUT,
            ),
            VatBookingDetail(
                booking_id=booking.booking_id,
                account_number="8400",
                net_amount=Decimal("65.42"),
                tax_amount=Decimal("4.58"),
                tax_rate=7,
                direction=VatBookingDirection.OUTPUT,
            ),
        )

        repository.add_details(
            details
        )

        loaded = repository.list_for_booking(
    booking.booking_id
)

    loaded_for_period = (
        repository.list_for_company_in_date_range(
            company_id=company.company_id,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )
    )

    assert loaded == details
    assert loaded_for_period == details
