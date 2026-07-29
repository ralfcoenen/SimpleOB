"""
Unit-Tests für den BookingValidator.
"""

from tests.factories import create_booking
from tests.factories import create_chart_of_accounts

from openbilanz.domain.booking_validator import BookingValidator


def test_accepts_booking_when_all_accounts_exist() -> None:
    """
    Eine Buchung mit ausschließlich vorhandenen Konten
    wird akzeptiert.
    """
    chart = create_chart_of_accounts()
    booking = create_booking()

    validator = BookingValidator(chart)

    validator.validate(booking)
    
