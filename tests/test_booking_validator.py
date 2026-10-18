import pytest

from simpleob.domain.booking import Booking
from simpleob.domain.booking_validator import BookingValidator
from simpleob.domain.errors import (
    UnknownAccountError,
)
from tests.factories import (
    create_booking,
    create_booking_line,
    create_chart_of_accounts,
)


def test_accepts_booking_when_all_accounts_exist() -> None:
    """
    Eine Buchung mit ausschließlich vorhandenen Konten
    wird akzeptiert.
    """
    chart = create_chart_of_accounts()
    booking = create_booking()

    validator = BookingValidator(chart)

    validator.validate(booking)


def test_rejects_booking_with_unknown_account() -> None:
    """
    Eine Buchung mit einem unbekannten Konto
    wird abgelehnt.
    """
    chart = create_chart_of_accounts()
    booking = create_booking()

    unknown_line = create_booking_line(
        account_number="9999",
        side=booking.lines[0].side,
        amount=booking.lines[0].amount,
    )

    booking_with_unknown_account = Booking(
        booking_date=booking.booking_date,
        voucher_no=booking.voucher_no,
        description=booking.description,
        lines=(
            unknown_line,
            booking.lines[1],
        ),
    )

    validator = BookingValidator(chart)

    with pytest.raises(UnknownAccountError):
        validator.validate(booking_with_unknown_account)
        
