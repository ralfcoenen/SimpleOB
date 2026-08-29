"""Tests für die zeitliche Zuordnung der USt-Voranmeldung."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_booking_direction import (
    VatBookingDirection,
)
from openbilanz.domain.vat_payment_allocation import (
    VatPaymentAllocation,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue import VatRevenue
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
from openbilanz.domain.vat_taxation_method import (
    VatTaxationMethod,
)
from openbilanz.services.vat_advance_return_timing_service import (
    VatAdvanceReturnTimingService,
)


def _booking(
    *,
    booking_id,
    booking_date: date,
) -> Booking:
    return Booking(
        booking_id=booking_id,
        booking_date=booking_date,
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("1.00"),
            ),
            BookingLine(
                account_number="1400",
                side=EntrySide.CREDIT,
                amount=Decimal("1.00"),
            ),
        ),
    )


def test_uses_service_date_for_agreed_taxation() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()
    booking_id = uuid4()

    revenue = VatRevenue(
        booking_id=booking_id,
        gross_amount=Decimal("119.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 1, 15),
    )

    output_detail = VatBookingDetail(
        booking_id=booking_id,
        account_number="8400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.OUTPUT,
    )

    input_detail = VatBookingDetail(
        booking_id=uuid4(),
        account_number="3400",
        net_amount=Decimal("50.00"),
        tax_amount=Decimal("9.50"),
        tax_rate=19,
        direction=VatBookingDirection.INPUT,
    )

    revenue_repository.list_revenues_for_company_in_date_range.return_value = (
        revenue,
    )
    detail_repository.list_for_booking.return_value = (
        output_detail,
    )
    detail_repository.list_for_company_in_date_range.return_value = (
        input_detail,
    )

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.AGREED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result == (
        output_detail,
        input_detail,
    )

    revenue_repository.list_revenues_for_company_in_date_range.assert_called_once_with(
        company_id=company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )


def test_uses_booking_date_for_immediate_received_taxation() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()
    booking_id = uuid4()

    revenue = VatRevenue(
        booking_id=booking_id,
        gross_amount=Decimal("119.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.IMMEDIATE,
        service_date=date(2025, 12, 20),
    )

    output_detail = VatBookingDetail(
        booking_id=booking_id,
        account_number="8400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.OUTPUT,
    )

    revenue_repository.list_revenues_for_company.return_value = (
        revenue,
    )
    revenue_repository.list_allocations_for_revenue.return_value = ()
    detail_repository.list_for_booking.return_value = (
        output_detail,
    )
    detail_repository.list_for_company_in_date_range.return_value = ()

    booking_repository.get.return_value = _booking(
        booking_id=booking_id,
        booking_date=date(2026, 1, 5),
    )

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.RECEIVED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result == (
        output_detail,
    )


def test_allocates_partial_payment_for_received_taxation() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()
    invoice_booking_id = uuid4()
    payment_booking_id = uuid4()

    revenue = VatRevenue(
        booking_id=invoice_booking_id,
        gross_amount=Decimal("119.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2025, 12, 20),
    )

    output_detail = VatBookingDetail(
        booking_id=invoice_booking_id,
        account_number="8400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.OUTPUT,
    )

    allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=payment_booking_id,
        amount=Decimal("59.50"),
    )

    revenue_repository.list_revenues_for_company.return_value = (
        revenue,
    )
    revenue_repository.list_allocations_for_revenue.return_value = (
        allocation,
    )

    detail_repository.list_for_booking.return_value = (
        output_detail,
    )
    detail_repository.list_for_company_in_date_range.return_value = ()

    booking_repository.get.return_value = _booking(
        booking_id=payment_booking_id,
        booking_date=date(2026, 1, 10),
    )

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.RECEIVED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result == (
        VatBookingDetail(
            booking_id=invoice_booking_id,
            account_number="8400",
            net_amount=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            tax_rate=19,
            direction=VatBookingDirection.OUTPUT,
        ),
    )


def test_allocates_mixed_rates_proportionally() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()
    invoice_booking_id = uuid4()
    payment_booking_id = uuid4()

    revenue = VatRevenue(
        booking_id=invoice_booking_id,
        gross_amount=Decimal("226.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2025, 12, 20),
    )

    detail_19 = VatBookingDetail(
        booking_id=invoice_booking_id,
        account_number="8400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.OUTPUT,
    )

    detail_7 = VatBookingDetail(
        booking_id=invoice_booking_id,
        account_number="8410",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("7.00"),
        tax_rate=7,
        direction=VatBookingDirection.OUTPUT,
    )

    allocation = VatPaymentAllocation(
        revenue_id=revenue.revenue_id,
        payment_booking_id=payment_booking_id,
        amount=Decimal("113.00"),
    )

    revenue_repository.list_revenues_for_company.return_value = (
        revenue,
    )
    revenue_repository.list_allocations_for_revenue.return_value = (
        allocation,
    )

    detail_repository.list_for_booking.return_value = (
        detail_19,
        detail_7,
    )
    detail_repository.list_for_company_in_date_range.return_value = ()

    booking_repository.get.return_value = _booking(
        booking_id=payment_booking_id,
        booking_date=date(2026, 1, 10),
    )

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.RECEIVED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result == (
        VatBookingDetail(
            booking_id=invoice_booking_id,
            account_number="8400",
            net_amount=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            tax_rate=19,
            direction=VatBookingDirection.OUTPUT,
        ),
        VatBookingDetail(
            booking_id=invoice_booking_id,
            account_number="8410",
            net_amount=Decimal("50.00"),
            tax_amount=Decimal("3.50"),
            tax_rate=7,
            direction=VatBookingDirection.OUTPUT,
        ),
    )


def test_cumulative_rounding_reaches_exact_invoice_amount() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()
    invoice_booking_id = uuid4()
    payment_1_id = uuid4()
    payment_2_id = uuid4()
    payment_3_id = uuid4()

    revenue = VatRevenue(
        booking_id=invoice_booking_id,
        gross_amount=Decimal("119.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.RECEIVABLE,
        service_date=date(2026, 1, 1),
    )

    output_detail = VatBookingDetail(
        booking_id=invoice_booking_id,
        account_number="8400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.OUTPUT,
    )

    allocations = (
        VatPaymentAllocation(
            revenue_id=revenue.revenue_id,
            payment_booking_id=payment_1_id,
            amount=Decimal("40.00"),
        ),
        VatPaymentAllocation(
            revenue_id=revenue.revenue_id,
            payment_booking_id=payment_2_id,
            amount=Decimal("40.00"),
        ),
        VatPaymentAllocation(
            revenue_id=revenue.revenue_id,
            payment_booking_id=payment_3_id,
            amount=Decimal("39.00"),
        ),
    )

    revenue_repository.list_revenues_for_company.return_value = (
        revenue,
    )
    revenue_repository.list_allocations_for_revenue.return_value = (
        allocations
    )

    detail_repository.list_for_booking.return_value = (
        output_detail,
    )
    detail_repository.list_for_company_in_date_range.return_value = ()

    bookings = {
        payment_1_id: _booking(
            booking_id=payment_1_id,
            booking_date=date(2026, 1, 5),
        ),
        payment_2_id: _booking(
            booking_id=payment_2_id,
            booking_date=date(2026, 1, 10),
        ),
        payment_3_id: _booking(
            booking_id=payment_3_id,
            booking_date=date(2026, 1, 15),
        ),
    }

    booking_repository.get.side_effect = bookings.get

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.RECEIVED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert sum(
        (
            detail.net_amount
            for detail in result
        ),
        start=Decimal("0.00"),
    ) == Decimal("100.00")

    assert sum(
        (
            detail.tax_amount
            for detail in result
        ),
        start=Decimal("0.00"),
    ) == Decimal("19.00")


def test_keeps_input_tax_on_existing_booking_date_path() -> None:
    booking_repository = Mock()
    detail_repository = Mock()
    revenue_repository = Mock()

    company_id = uuid4()

    input_detail = VatBookingDetail(
        booking_id=uuid4(),
        account_number="3400",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        tax_rate=19,
        direction=VatBookingDirection.INPUT,
    )

    detail_repository.list_for_company_in_date_range.return_value = (
        input_detail,
    )
    revenue_repository.list_revenues_for_company.return_value = ()

    service = VatAdvanceReturnTimingService(
        booking_repository=booking_repository,
        vat_booking_detail_repository=detail_repository,
        vat_revenue_repository=revenue_repository,
    )

    result = service.details_for_period(
        company_id=company_id,
        taxation_method=VatTaxationMethod.RECEIVED,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result == (
        input_detail,
    )
