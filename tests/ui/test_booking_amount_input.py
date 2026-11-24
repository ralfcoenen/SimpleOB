"""Regressionstests für Betragseingaben in der Buchungsmaske."""

from decimal import Decimal

from PySide6.QtWidgets import QApplication

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt.booking_frame import BookingFrame


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _frame(on_booking_created=lambda *_args: None) -> BookingFrame:
    accounts = (
        Account(TemplateAccount("1200", "Bank", AccountType.ASSET)),
        Account(TemplateAccount("8400", "Erlöse", AccountType.REVENUE)),
    )
    return BookingFrame(
        accounts=accounts,
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=on_booking_created,
    )


def test_integer_amount_input_is_cents_and_formatting_is_idempotent() -> None:
    _app()
    frame = _frame()
    amount_entry = frame._rows[0].debit_entry

    amount_entry.setText("123400")
    frame._normalize_amount_entry(amount_entry)

    assert amount_entry.text() == "1.234,00"
    assert amount_entry.property("amountNormalized") is True
    assert frame._parse_amount(
        amount_entry.text(),
        normalized=True,
    ) == Decimal("1234.00")

    frame._normalize_amount_entry(amount_entry)
    assert amount_entry.text() == "1.234,00"

    frame.close()


def test_explicit_decimal_comma_is_interpreted_as_entered() -> None:
    _app()
    frame = _frame()
    amount_entry = frame._rows[0].debit_entry

    amount_entry.setText("1234,00")
    frame._normalize_amount_entry(amount_entry)

    assert amount_entry.text() == "1.234,00"
    assert frame._parse_amount(
        amount_entry.text(),
        normalized=True,
    ) == Decimal("1234.00")

    frame.close()


def test_focus_changes_do_not_reinterpret_a_formatted_amount() -> None:
    app = _app()
    frame = _frame()
    frame.show()
    app.processEvents()
    amount_entry = frame._rows[0].debit_entry

    amount_entry.setText("123400")
    amount_entry.setFocus()
    amount_entry.editingFinished.emit()
    app.processEvents()
    assert amount_entry.text() == "1.234,00"

    frame._description_entry.setFocus()
    app.processEvents()
    amount_entry.setFocus()
    amount_entry.editingFinished.emit()
    app.processEvents()

    assert amount_entry.text() == "1.234,00"
    assert frame._parse_amount(
        amount_entry.text(),
        normalized=bool(amount_entry.property("amountNormalized")),
    ) == Decimal("1234.00")

    frame.close()


def test_formatted_amount_can_be_replaced_and_corrected_repeatedly() -> None:
    _app()
    frame = _frame()
    amount_entry = frame._rows[0].debit_entry

    for value, expected in (
        ("1", "0,01"),
        ("1234", "12,34"),
        ("123400", "1.234,00"),
        ("1234567", "12.345,67"),
        ("12", "0,12"),
    ):
        amount_entry.setText(value)
        frame._normalize_amount_entry(amount_entry)
        assert amount_entry.text() == expected

    frame.close()


def test_booking_is_saved_only_when_booking_transfer_succeeds() -> None:
    app = _app()
    received = []
    frame = _frame(lambda booking, positions: received.append((booking, positions)))
    frame.show()
    app.processEvents()
    frame._description_entry.setText("Testbuchung")
    debit_row = frame._rows[0]
    debit_row.account_entry.setText("1200")
    debit_row.debit_entry.setText("123400")
    frame._normalize_amount_entry(debit_row.debit_entry)
    credit_row = frame._rows[1]
    credit_row.account_entry.setText("8400")
    credit_row.credit_entry.setText("1234,00")

    assert received == []
    assert debit_row.debit_entry.isEnabled()
    assert debit_row.credit_entry.isEnabled()

    debit_row.debit_entry.setFocus()
    app.processEvents()
    frame._voucher_no_entry.setFocus()
    app.processEvents()
    assert received == []

    frame._create_booking()

    assert len(received) == 1
    booking, contribution_positions = received[0]
    assert booking.lines[0].amount == Decimal("1234.00")
    assert booking.lines[1].amount == Decimal("1234.00")
    assert contribution_positions == ()

    # Nach der Übernahme verhindert die Validierung den Callback bei ungültigen Werten.
    invalid_frame = _frame(lambda booking, positions: received.append((booking, positions)))
    invalid_frame._description_entry.setText("Ungültige Testbuchung")
    invalid_debit = invalid_frame._rows[0]
    invalid_debit.account_entry.setText("1200")
    invalid_debit.debit_entry.setText("0")
    invalid_credit = invalid_frame._rows[1]
    invalid_credit.account_entry.setText("8400")
    invalid_credit.credit_entry.setText("1")
    invalid_frame._create_booking()

    assert len(received) == 1
    frame.close()
    invalid_frame.close()
