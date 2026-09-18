"""Tests für Abschreibungsbuchungen."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)


def test_builds_closing_booking_from_proposal() -> None:
    proposal = DepreciationProposal(
        fixed_asset_id=uuid4(),
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("800.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    booking = (
        DepreciationBookingService()
        .build_booking(
            proposal=proposal,
            asset_code="A-0001",
            asset_description="MacBook Pro",
        )
    )

    assert booking.booking_date == date(
        2026,
        12,
        31,
    )
    assert booking.booking_type is BookingType.REGULAR
    assert booking.description == (
        "Lineare Abschreibung – "
        "A-0001 – MacBook Pro"
    )

    assert len(booking.lines) == 2

    assert booking.lines[0].account_number == "4830"
    assert booking.lines[0].side is EntrySide.DEBIT
    assert booking.lines[0].amount == Decimal("800.00")

    assert booking.lines[1].account_number == "0690"
    assert booking.lines[1].side is EntrySide.CREDIT
    assert booking.lines[1].amount == Decimal("800.00")

def test_rejects_invalid_proposal() -> None:
    with pytest.raises(TypeError):
        DepreciationBookingService().build_booking(
            proposal="invalid",  # type: ignore[arg-type]
            asset_code="A-0001",
            asset_description="MacBook Pro",
        )
