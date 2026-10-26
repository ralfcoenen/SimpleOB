from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QMessageBox

from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.main_window import MainWindow


def _account_roles(
    *,
    receivables: frozenset[str] = frozenset(),
    payables: frozenset[str] = frozenset(),
    customer_credits: frozenset[str] = frozenset(),
    supplier_credits: frozenset[str] = frozenset(),
) -> AccountingAccountRoles:
    return AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset(),
        general_rate_sales_accounts=frozenset(),
        customer_receivables=receivables,
        supplier_payables=payables,
        customer_credit_balances=customer_credits,
        supplier_credit_balances=supplier_credits,
    )


def _booking(*lines: BookingLine, description: str = "Manuelle Begründung") -> Booking:
    return Booking(
        booking_date=date(2026, 10, 26),
        description=description,
        lines=tuple(lines),
    )


def _window(roles: AccountingAccountRoles) -> Mock:
    window = Mock()
    window._workspace.is_closed = False
    window._workspace.load_account_configuration.return_value = (
        object(),
        object(),
        roles,
    )
    window._confirm_op_control_account_booking = lambda booking: (
        MainWindow._confirm_op_control_account_booking(window, booking)
    )
    return window


def _balanced_booking(account_number: str = "1000") -> Booking:
    return _booking(
        BookingLine(account_number, EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
    )


def test_regular_manual_booking_does_not_show_op_confirmation(monkeypatch):
    warning = Mock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(_account_roles(receivables=frozenset({"1500"})))

    MainWindow._post_booking(window, _balanced_booking())

    warning.assert_not_called()
    window._workspace.post_booking.assert_called_once()


def test_confirmed_control_account_booking_is_posted_once(monkeypatch):
    warning = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(_account_roles(receivables=frozenset({"1500"})))
    booking = _booking(
        BookingLine("1500", EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
    )

    MainWindow._post_booking(window, booking)

    warning.assert_called_once()
    assert "1500" in warning.call_args.args[2]
    assert "Kundenforderungen" in warning.call_args.args[2]
    assert "ausschließlich im Hauptbuch" in warning.call_args.args[2]
    assert "ungeklärt" in warning.call_args.args[2]
    assert booking.description in warning.call_args.args[2]
    window._workspace.post_booking.assert_called_once()


def test_rejected_control_account_confirmation_does_not_post(monkeypatch):
    warning = Mock(return_value=QMessageBox.StandardButton.No)
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(_account_roles(receivables=frozenset({"1500"})))
    booking = _booking(
        BookingLine("1500", EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
    )

    MainWindow._post_booking(window, booking)

    warning.assert_called_once()
    window._workspace.post_booking.assert_not_called()
    window._refresh_accounts.assert_not_called()


def test_multiple_control_account_lines_show_one_confirmation_with_all_roles(
    monkeypatch,
):
    warning = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(
        _account_roles(
            receivables=frozenset({"1500"}),
            payables=frozenset({"3300"}),
        )
    )
    booking = _booking(
        BookingLine("1500", EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("3300", EntrySide.DEBIT, Decimal("5.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("15.00")),
    )

    MainWindow._post_booking(window, booking)

    warning.assert_called_once()
    message = warning.call_args.args[2]
    assert "1500" in message
    assert "Kundenforderungen" in message
    assert "3300" in message
    assert "Lieferantenverbindlichkeiten" in message
    window._workspace.post_booking.assert_called_once()


def test_control_account_detection_uses_current_mandant_roles(monkeypatch):
    warning = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(_account_roles(customer_credits=frozenset({"1597"})))
    booking = _booking(
        BookingLine("1597", EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
    )

    MainWindow._post_booking(window, booking)

    window._workspace.load_account_configuration.assert_called_once_with()
    warning.assert_called_once()
    assert "1597" in warning.call_args.args[2]
    assert "Kundenguthaben" in warning.call_args.args[2]
    window._workspace.post_booking.assert_called_once()


@pytest.mark.parametrize("description", [None, "", "   "])
def test_control_account_booking_requires_existing_booking_text(
    monkeypatch,
    description,
):
    warning = Mock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warning)
    window = _window(_account_roles(receivables=frozenset({"1500"})))
    booking = _booking(
        BookingLine("1500", EntrySide.DEBIT, Decimal("10.00")),
        BookingLine("8400", EntrySide.CREDIT, Decimal("10.00")),
        description=description,
    )

    MainWindow._post_booking(window, booking)

    warning.assert_called_once()
    assert "Begründung" in warning.call_args.args[1]
    window._workspace.post_booking.assert_not_called()
