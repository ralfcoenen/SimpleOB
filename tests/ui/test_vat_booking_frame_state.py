"""Tests für die Schreibschutz- und Freigabesteuerung des VatBookingFrame."""

from unittest.mock import Mock

from openbilanz.domain.account_type import AccountType
from openbilanz.ui.vat_booking_frame import (
    VatBookingFrame,
    _INPUT_INVOICE,
)


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


def test_input_invoice_accepts_asset_account() -> None:
    """Eine Eingangsrechnung darf auf ein Aktivkonto gebucht werden."""

    frame = object.__new__(VatBookingFrame)

    frame._enabled = True
    frame._booking_button = Mock()
    frame._status_var = Mock()

    frame._booking_date_var = Mock()
    frame._booking_date_var.get.return_value = "01.09.2026"

    frame._booking_description_var = Mock()
    frame._booking_description_var.get.return_value = "Maschine"

    frame._counter_account_var = Mock()
    frame._counter_account_var.get.return_value = "1200"

    frame._invoice_type_var = Mock()
    frame._invoice_type_var.get.return_value = _INPUT_INVOICE

    asset_account_var = Mock()
    asset_account_var.get.return_value = "0400"

    amount_var = Mock()
    amount_var.get.return_value = "1.190,00"

    tax_rate_var = Mock()
    tax_rate_var.get.return_value = "19 %"

    frame._position_rows = [
        {
            "account_var": asset_account_var,
            "amount_var": amount_var,
            "tax_rate_var": tax_rate_var,
        }
    ]

    counter_account = Mock()
    counter_account.number = "1200"

    asset_account = Mock()
    asset_account.number = "0400"
    asset_account.account_type = AccountType.ASSET

    def resolve_account(value: str) -> Mock | None:
        if value == "1200":
            return counter_account

        if value == "0400":
            return asset_account

        return None

    frame._resolve_account = Mock(side_effect=resolve_account)

    VatBookingFrame._on_form_changed(frame)

    frame._booking_button.state.assert_called_once_with(
        ["!disabled"]
    )
