"""Tests für die atomare Verbuchung von USt-Ausgangsumsätzen."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_booking_detail import VatBookingDetail
from openbilanz.domain.vat_booking_direction import (
    VatBookingDirection,
)
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
from openbilanz.services.vat_revenue_posting_workflow import (
    VatRevenuePostingWorkflow,
)


def _booking() -> Booking:
    return Booking(
        booking_date=date(2026, 8, 27),
        lines=(
            BookingLine(
                account_number="1400",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )


def _booking_details(
    booking: Booking,
) -> tuple[VatBookingDetail, ...]:
    return (
        VatBookingDetail(
            booking_id=booking.booking_id,
            account_number="8400",
            net_amount=Decimal("840.34"),
            tax_amount=Decimal("159.66"),
            tax_rate=19,
            direction=VatBookingDirection.OUTPUT,
        ),
    )


def test_posts_booking_and_revenue_in_one_transaction() -> None:
    session = Mock()
    booking_repository = Mock()
    vat_booking_detail_repository = Mock()
    vat_revenue_repository = Mock()

    company = Company(
        company_id=uuid4(),
        name="Test UG",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    booking = _booking()
    booking_details = _booking_details(
        booking
    )

    workflow = VatRevenuePostingWorkflow(
        session=session,
        booking_repository=booking_repository,
        vat_booking_detail_repository=(
            vat_booking_detail_repository
        ),
        vat_revenue_repository=vat_revenue_repository,
    )

    revenue = workflow.post(
        company=company,
        fiscal_year=fiscal_year,
        booking=booking,
        booking_details=booking_details,
        gross_amount=Decimal("1000.00"),
        revenue_kind=VatRevenueKind.NORMAL,
        payment_kind=VatPaymentKind.IMMEDIATE,
        service_date=date(2026, 8, 27),
    )

    booking_repository.add.assert_called_once_with(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=booking,
        commit=False,
    )

    vat_booking_detail_repository.add_details.assert_called_once_with(
        booking_details,
        commit=False,
    )

    vat_revenue_repository.add_revenue.assert_called_once_with(
        revenue,
        commit=False,
    )

    assert revenue.booking_id == booking.booking_id
    assert revenue.gross_amount == Decimal("1000.00")
    assert revenue.revenue_kind is VatRevenueKind.NORMAL
    assert revenue.payment_kind is VatPaymentKind.IMMEDIATE

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_rolls_back_when_revenue_persistence_fails() -> None:
    session = Mock()
    booking_repository = Mock()
    vat_booking_detail_repository = Mock()
    vat_revenue_repository = Mock()

    company = Company(
        company_id=uuid4(),
        name="Test UG",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    booking = _booking()
    booking_details = _booking_details(
        booking
    )

    vat_revenue_repository.add_revenue.side_effect = RuntimeError(
        "Speichern fehlgeschlagen"
    )

    workflow = VatRevenuePostingWorkflow(
        session=session,
        booking_repository=booking_repository,
        vat_booking_detail_repository=(
            vat_booking_detail_repository
        ),
        vat_revenue_repository=vat_revenue_repository,
    )

    with pytest.raises(
        RuntimeError,
        match="Speichern fehlgeschlagen",
    ):
        workflow.post(
            company=company,
            fiscal_year=fiscal_year,
            booking=booking,
            booking_details=booking_details,
            gross_amount=Decimal("1000.00"),
            revenue_kind=VatRevenueKind.NORMAL,
            payment_kind=VatPaymentKind.IMMEDIATE,
            service_date=date(2026, 8, 27),
        )

    booking_repository.add.assert_called_once_with(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=booking,
        commit=False,
    )

    vat_booking_detail_repository.add_details.assert_called_once_with(
        booking_details,
        commit=False,
    )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
