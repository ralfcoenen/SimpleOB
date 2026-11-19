from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.ui_qt.main_window import MainWindow


def test_general_booking_posts_without_op_specific_confirmation():
    window = Mock()
    window._workspace.is_closed = False
    booking = Booking(
        booking_date=date(2026, 10, 26),
        description=None,
        lines=(
            BookingLine("1500", EntrySide.DEBIT, Decimal("10.00")),
            BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
        ),
    )

    MainWindow._post_booking(window, booking)

    window._workspace.post_booking.assert_called_once_with(
        booking,
        equity_contribution_line_positions=(),
        chart_of_accounts=None,
    )
    window._workspace.load_account_configuration.assert_not_called()
    window._refresh_kr_monitoring.assert_called_once()
    window._refresh_accounts.assert_called_once()
    window._refresh_journal.assert_called_once()
    window._refresh_balance_sheet.assert_called_once()
