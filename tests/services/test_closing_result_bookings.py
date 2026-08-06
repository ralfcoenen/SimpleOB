from dataclasses import is_dataclass
from datetime import date
from decimal import Decimal

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.closing_result import ClosingResult


def test_closing_result_can_contain_bookings() -> None:
    booking = Booking(
        booking_date=date(2026, 12, 31),
        voucher_no="AB-001",
        description="Abschlussbuchung",
        lines=(
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="9000",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    result = ClosingResult(
        net_income=Decimal("300.00"),
        bookings=(booking,),
    )

    assert is_dataclass(result)
    assert result.bookings == (booking,)
    
