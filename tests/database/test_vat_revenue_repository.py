"""Tests für umsatzsteuerliche Ausgangsumsätze."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.database.vat_revenue_repository import (
    VatRevenueRepository,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_payment_allocation import (
    VatPaymentAllocation,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind


def _booking(
    *,
    booking_date: date,
    debit_account: str,
    credit_account: str,
    amount: Decimal,
) -> Booking:
    """Erzeugt eine einfache ausgeglichene Testbuchung."""

    return Booking(
        booking_date=booking_date,
        lines=(
            BookingLine(
                account_number=debit_account,
                side=EntrySide.DEBIT,
                amount=amount,
            ),
            BookingLine(
                account_number=credit_account,
                side=EntrySide.CREDIT,
                amount=amount,
            ),
        ),
    )


def test_saves_and_loads_vat_revenue() -> None:
    """Ein Ausgangsumsatz kann gespeichert und geladen werden."""

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
            booking_date=date(2026, 8, 1),
            debit_account="1400",
            credit_account="8400",
            amount=Decimal("1000.00"),
        )

        BookingRepository(session).add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=booking,
        )

        repository = VatRevenueRepository(
            session
        )

        revenue = VatRevenue(
            booking_id=booking.booking_id,
            gross_amount=Decimal("1000.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.RECEIVABLE,
            service_date=date(2026, 8, 1),
        )

        repository.add_revenue(
            revenue
        )

        loaded = repository.get_revenue(
            revenue.revenue_id
        )

    assert loaded == revenue


def test_saves_partial_payment_allocation() -> None:
    """Eine Teilzahlung kann einem Ausgangsumsatz zugeordnet werden."""

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

        booking_repository = BookingRepository(
            session
        )

        invoice = _booking(
            booking_date=date(2026, 8, 1),
            debit_account="1400",
            credit_account="8400",
            amount=Decimal("1000.00"),
        )

        payment = _booking(
            booking_date=date(2026, 8, 10),
            debit_account="1200",
            credit_account="1400",
            amount=Decimal("600.00"),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=invoice,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=payment,
        )

        repository = VatRevenueRepository(
            session
        )

        revenue = VatRevenue(
            booking_id=invoice.booking_id,
            gross_amount=Decimal("1000.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.RECEIVABLE,
            service_date=date(2026, 8, 1),
        )

        repository.add_revenue(
            revenue
        )

        allocation = VatPaymentAllocation(
            revenue_id=revenue.revenue_id,
            payment_booking_id=payment.booking_id,
            amount=Decimal("600.00"),
        )

        repository.add_payment_allocation(
            allocation
        )

        loaded = (
            repository.list_allocations_for_revenue(
                revenue.revenue_id
            )
        )

    assert loaded == (allocation,)


def test_rejects_payment_allocation_above_revenue() -> None:
    """Zahlungszuordnungen dürfen den Umsatz nicht überschreiten."""

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

        booking_repository = BookingRepository(
            session
        )

        invoice = _booking(
            booking_date=date(2026, 8, 1),
            debit_account="1400",
            credit_account="8400",
            amount=Decimal("1000.00"),
        )

        payment = _booking(
            booking_date=date(2026, 8, 10),
            debit_account="1200",
            credit_account="1400",
            amount=Decimal("1100.00"),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=invoice,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=payment,
        )

        repository = VatRevenueRepository(
            session
        )

        revenue = VatRevenue(
            booking_id=invoice.booking_id,
            gross_amount=Decimal("1000.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.RECEIVABLE,
            service_date=date(2026, 8, 1),
        )

        repository.add_revenue(
            revenue
        )

        allocation = VatPaymentAllocation(
            revenue_id=revenue.revenue_id,
            payment_booking_id=payment.booking_id,
            amount=Decimal("1100.00"),
        )

        with pytest.raises(
            ValueError,
            match=(
                "Die Zahlungszuordnungen überschreiten "
                "den Ausgangsumsatz."
            ),
        ):
            repository.add_payment_allocation(
                allocation
            )


def test_lists_company_revenues_in_date_range() -> None:
    """Es werden nur Umsätze des Mandanten im Zeitraum geladen."""

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

    fiscal_year_2025 = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    fiscal_year_2026 = FiscalYear(
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
            fiscal_year_2025,
        )

        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year_2026,
        )

        booking_repository = BookingRepository(
            session
        )

        booking_2025 = _booking(
            booking_date=date(2025, 12, 31),
            debit_account="1400",
            credit_account="8400",
            amount=Decimal("500.00"),
        )

        booking_2026 = _booking(
            booking_date=date(2026, 1, 15),
            debit_account="1400",
            credit_account="8400",
            amount=Decimal("1000.00"),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year_2025,
            booking=booking_2025,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year_2026,
            booking=booking_2026,
        )

        repository = VatRevenueRepository(
            session
        )

        revenue_2025 = VatRevenue(
            booking_id=booking_2025.booking_id,
            gross_amount=Decimal("500.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.IMMEDIATE,
            service_date=date(2025, 12, 31),
        )

        revenue_2026 = VatRevenue(
            booking_id=booking_2026.booking_id,
            gross_amount=Decimal("1000.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.IMMEDIATE,
            service_date=date(2026, 1, 15),
        )

        repository.add_revenue(
            revenue_2025
        )

        repository.add_revenue(
            revenue_2026
        )

        loaded = (
            repository.list_revenues_for_company_in_date_range(
                company_id=company.company_id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )
        )

    assert loaded == (revenue_2026,)
