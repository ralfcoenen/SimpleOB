"""Tests für die Schreibschutzsteuerung des VatBookingFrame."""

from unittest.mock import Mock

from openbilanz.ui.vat_booking_frame import VatBookingFrame


def _create_frame_double() -> VatBookingFrame:
    """Erzeugt einen VatBookingFrame ohne Tkinter-Fenster."""

    frame = object.__new__(VatBookingFrame)

    frame._enabled = True
    frame._booking_date_entry = Mock()
    frame._voucher_no_entry = Mock()
    frame._description_entry = Mock()
    frame._counter_account_box = Mock()
    frame._booking_button = Mock()
    frame._status_var = Mock()

    frame._on_form_changed = Mock()

    return frame


def test_set_enabled_enables_booking_inputs() -> None:
    frame = _create_frame_double()

    frame.set_enabled(True)

    assert frame._enabled is True

    frame._booking_date_entry.configure.assert_called_once_with(
        state="normal"
    )
    frame._voucher_no_entry.configure.assert_called_once_with(
        state="normal"
    )
    frame._description_entry.configure.assert_called_once_with(
        state="normal"
    )
    frame._counter_account_box.configure.assert_called_once_with(
        state="normal"
    )

    frame._on_form_changed.assert_called_once_with()


def test_set_enabled_disables_booking_inputs() -> None:
    frame = _create_frame_double()

    frame.set_enabled(False)

    assert frame._enabled is False

    frame._booking_date_entry.configure.assert_called_once_with(
        state="disabled"
    )
    frame._voucher_no_entry.configure.assert_called_once_with(
        state="disabled"
    )
    frame._description_entry.configure.assert_called_once_with(
        state="disabled"
    )
    frame._counter_account_box.configure.assert_called_once_with(
        state="disabled"
    )

    frame._booking_button.state.assert_called_once_with(
        ["disabled"]
    )

    frame._status_var.set.assert_called_once_with(
        "Das Geschäftsjahr ist abgeschlossen. "
        "Buchungen sind nicht mehr möglich."
    )

    frame._on_form_changed.assert_not_called()
