from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QDialog

from simpleob.ui_qt.main_window import MainWindow


def _payment_window(calls, dialog_result):
    class Dialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return dialog_result

    return SimpleNamespace(
        _open_item_payment_service=object(),
        _workspace=SimpleNamespace(
            is_closed=False,
            reload=lambda: calls.append("workspace reload"),
        ),
        _context=SimpleNamespace(
            company=SimpleNamespace(company_id=uuid4()),
            fiscal_year=object(),
        ),
        _accounts=(),
        _refresh_kr_monitoring=lambda: calls.append("KR"),
        _refresh_accounts=lambda: calls.append("accounts"),
        _refresh_journal=lambda: calls.append("journal"),
        _refresh_balance_sheet=lambda: calls.append("balance sheet"),
        _refresh_visible_open_item_view=lambda: calls.append("open items"),
        _dialog_class=Dialog,
    )


def test_successful_customer_payment_refreshes_kr_once_after_dialog_success(
    monkeypatch,
):
    calls = []
    window = _payment_window(calls, QDialog.DialogCode.Accepted)
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.OpenItemPaymentDialog",
        window._dialog_class,
    )

    MainWindow._open_payment_dialog(window)

    assert calls == [
        "KR",
        "workspace reload",
        "accounts",
        "journal",
        "balance sheet",
        "open items",
    ]


def test_cancelled_or_failed_payment_dialog_does_not_refresh_kr(monkeypatch):
    calls = []
    window = _payment_window(calls, QDialog.DialogCode.Rejected)
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.OpenItemPaymentDialog",
        window._dialog_class,
    )

    MainWindow._open_payment_dialog(window)

    assert calls == []


def test_booking_failure_does_not_refresh_kr_and_success_refreshes_after_post():
    calls = []

    def failed_post(*_args, **_kwargs):
        calls.append("post attempted")
        raise RuntimeError("posting failed")

    failed_window = SimpleNamespace(
        _workspace=SimpleNamespace(is_closed=False, post_booking=failed_post),
        _confirm_op_control_account_booking=lambda _booking: True,
        _refresh_kr_monitoring=lambda: calls.append("KR"),
    )
    with pytest.raises(RuntimeError, match="posting failed"):
        MainWindow._post_booking(failed_window, object())
    assert calls == ["post attempted"]

    calls.clear()
    successful_window = SimpleNamespace(
        _workspace=SimpleNamespace(
            is_closed=False,
            post_booking=lambda *_args, **_kwargs: calls.append("posted"),
        ),
        _confirm_op_control_account_booking=lambda _booking: True,
        _refresh_kr_monitoring=lambda: calls.append("KR"),
        _refresh_accounts=lambda: calls.append("accounts"),
        _refresh_journal=lambda: calls.append("journal"),
        _refresh_balance_sheet=lambda: calls.append("balance sheet"),
    )

    MainWindow._post_booking(successful_window, object())

    assert calls == ["posted", "KR", "accounts", "journal", "balance sheet"]
