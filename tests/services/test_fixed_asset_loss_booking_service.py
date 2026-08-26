"""Tests für Verlustbuchungen von Anlagegütern."""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.fixed_asset_loss_booking_service import (
    FixedAssetLossBookingService,
)


def test_builds_fixed_asset_loss_booking() -> None:
    service = FixedAssetLossBookingService()

    booking = service.build_booking(
        loss_date=date(2026, 8, 15),
        book_value=Decimal("10000.00"),
        asset_account_number="0400",
        loss_expense_account_number="4840",
    )

    assert booking.booking_date == date(2026, 8, 15)
    assert booking.booking_type is BookingType.REGULAR
    assert booking.debit_total == Decimal("10000.00")
    assert booking.credit_total == Decimal("10000.00")

    assert len(booking.lines) == 2

    assert booking.lines[0].account_number == "4840"
    assert booking.lines[0].side is EntrySide.DEBIT
    assert booking.lines[0].amount == Decimal("10000.00")

    assert booking.lines[1].account_number == "0400"
    assert booking.lines[1].side is EntrySide.CREDIT
    assert booking.lines[1].amount == Decimal("10000.00")


def test_rejects_zero_book_value() -> None:
    service = FixedAssetLossBookingService()

    with pytest.raises(
        ValueError,
        match="book_value must be greater",
    ):
        service.build_booking(
            loss_date=date(2026, 8, 15),
            book_value=Decimal("0.00"),
            asset_account_number="0400",
            loss_expense_account_number="4840",
        )
