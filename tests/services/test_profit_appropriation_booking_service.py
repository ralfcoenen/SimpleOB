"""Tests für Ergebnisverwendungsbuchungen."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from openbilanz.services.profit_appropriation_booking_service import (
    ProfitAppropriationBookingService,
)


def test_builds_booking_from_profit_appropriation_proposal() -> None:
    proposal = ProfitAppropriationPostingProposal(
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
        booking_date=date(2027, 3, 15),
        amount=Decimal("5000.00"),
        debit_account_number="2970",
        credit_account_number="0755",
    )

    booking = (
        ProfitAppropriationBookingService()
        .build_booking(
            proposal=proposal
        )
    )

    assert booking.booking_date == date(2027, 3, 15)
    assert booking.booking_type is BookingType.REGULAR
    assert booking.description == (
        "Ergebnisverwendung – Ausschüttung"
    )

    assert len(booking.lines) == 2

    assert booking.lines[0].account_number == "2970"
    assert booking.lines[0].side is EntrySide.DEBIT
    assert booking.lines[0].amount == Decimal("5000.00")

    assert booking.lines[1].account_number == "0755"
    assert booking.lines[1].side is EntrySide.CREDIT
    assert booking.lines[1].amount == Decimal("5000.00")
