"""Tests für die Geschäftsjahressteuerung des MainWindow."""

from unittest.mock import Mock

from openbilanz.ui.main_window import MainWindow


def _create_window_double(
    *,
    is_open: bool,
) -> MainWindow:
    """Erzeugt ein MainWindow ohne Tkinter-Fenster."""

    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.is_open = is_open
    window._workspace.is_closed = not is_open

    window._opening_balance_button = Mock()
    window._booking_frame = Mock()

    return window


def test_open_fiscal_year_enables_editing() -> None:
    window = _create_window_double(
        is_open=True
    )

    window._update_editing_state()

    window._opening_balance_button.state.assert_called_once_with(
        ["!disabled"]
    )

    window._booking_frame.set_enabled.assert_called_once_with(
        True
    )


def test_closed_fiscal_year_disables_editing() -> None:
    window = _create_window_double(
        is_open=False
    )

    window._update_editing_state()

    window._opening_balance_button.state.assert_called_once_with(
        ["disabled"]
    )

    window._booking_frame.set_enabled.assert_called_once_with(
        False
    )
