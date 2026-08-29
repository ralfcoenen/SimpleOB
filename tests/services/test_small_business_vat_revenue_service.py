"""Tests für die §-19-Umsatzermittlung."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.vat_payment_allocation import (
    VatPaymentAllocation,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
from openbilanz.services.small_business_vat_revenue_service import (
    SmallBusinessVatRevenueService,
)


def _booking(
    *,
    booking_date: date,
    amount: Decimal,
) -> Booking:
    return Booking(
        booking_date=booking_date,
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=amount,
            ),
            BookingLine(
                account_number="1400",
                side=EntrySide.CREDIT,
                amount=amount,
            ),
        ),
    )


def test_counts_immediate_normal_revenue() -> None:
    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    booking = _booking(
        booking_date=date(2026, 8, 1),
        amount=Decimal("1000.00"),
    )

    revenue = VatRevenue(
        booking_id=booking.booking_id,
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.IMMEDIATE,
        service_date=date(2026, 8, 1),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )

    booking_repository.get.return_value = booking

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    result = service.revenue_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert result == Decimal("1000.00")


def test_counts_allocated_payment_for_receivable() -> None:
    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    revenue = VatRevenue(
        booking_id=uuid4(),
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 8, 1),
    )

    payment = _booking(
        booking_date=date(2026, 8, 10),
        amount=Decimal("600.00"),
    )

    allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=payment.booking_id,
        amount=Decimal("600.00"),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )
    repository.list_allocations_for_revenue.return_value = (
        allocation,
    )
    booking_repository.get.return_value = payment

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    result = service.revenue_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert result == Decimal("600.00")


def test_excludes_fixed_asset_disposal() -> None:
    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    revenue = VatRevenue(
        booking_id=uuid4(),
        gross_amount=Decimal("5000.00"),
        revenue_kind=(
            VatRevenueKind.FIXED_ASSET_DISPOSAL
        ),
        payment_kind=VatPaymentKind.IMMEDIATE,
        service_date=date(2026, 8, 1),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    result = service.revenue_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert result == Decimal("0.00")


def test_counts_payment_for_previous_year_receivable() -> None:
    """Eine Zahlung zählt auch bei Rechnung aus dem Vorjahr."""

    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    invoice = _booking(
        booking_date=date(2025, 12, 20),
        amount=Decimal("1000.00"),
    )

    payment = _booking(
        booking_date=date(2026, 1, 15),
        amount=Decimal("600.00"),
    )

    revenue = VatRevenue(
        booking_id=invoice.booking_id,
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2025, 12, 20),
    )

    allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=payment.booking_id,
        amount=Decimal("600.00"),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )

    repository.list_allocations_for_revenue.return_value = (
        allocation,
    )

    booking_repository.get.return_value = payment

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    result = service.revenue_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert result == Decimal("600.00")


def test_returns_revenue_events_in_chronological_order() -> None:
    """Vereinnahmte Umsätze werden chronologisch geliefert."""

    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    revenue = VatRevenue(
        booking_id=uuid4(),
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 1, 1),
    )

    first_payment = _booking(
        booking_date=date(2026, 3, 10),
        amount=Decimal("400.00"),
    )

    second_payment = _booking(
        booking_date=date(2026, 8, 20),
        amount=Decimal("600.00"),
    )

    first_allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=first_payment.booking_id,
        amount=Decimal("400.00"),
    )

    second_allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=second_payment.booking_id,
        amount=Decimal("600.00"),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )

    repository.list_allocations_for_revenue.return_value = (
        second_allocation,
        first_allocation,
    )

    booking_repository.get.side_effect = (
        lambda booking_id: {
            first_payment.booking_id: first_payment,
            second_payment.booking_id: second_payment,
        }[booking_id]
    )

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    events = service.revenue_events_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert tuple(
        (
            event.event_date,
            event.amount,
        )
        for event in events
    ) == (
        (
            date(2026, 3, 10),
            Decimal("400.00"),
        ),
        (
            date(2026, 8, 20),
            Decimal("600.00"),
        ),
    )


def test_sums_revenue_events_for_calendar_year() -> None:
    """Die Jahressumme entspricht der Summe der Umsatzereignisse."""

    repository = Mock()
    booking_repository = Mock()

    company_id = uuid4()

    revenue = VatRevenue(
        booking_id=uuid4(),
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 1, 1),
    )

    payment = _booking(
        booking_date=date(2026, 6, 1),
        amount=Decimal("600.00"),
    )

    allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=payment.booking_id,
        amount=Decimal("600.00"),
    )

    repository.list_revenues_for_company.return_value = (
        revenue,
    )

    repository.list_allocations_for_revenue.return_value = (
        allocation,
    )

    booking_repository.get.return_value = payment

    service = SmallBusinessVatRevenueService(
        vat_revenue_repository=repository,
        booking_repository=booking_repository,
    )

    result = service.revenue_for_calendar_year(
        company_id=company_id,
        calendar_year=2026,
    )

    assert result == Decimal("600.00")
