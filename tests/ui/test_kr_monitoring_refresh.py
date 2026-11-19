from types import SimpleNamespace

import pytest

from simpleob.ui_qt.main_window import MainWindow


def test_booking_refreshes_informative_monitor_only_after_successful_post():
    calls = []

    def failed_post(*_args, **_kwargs):
        calls.append("post attempted")
        raise RuntimeError("posting failed")

    failed_window = SimpleNamespace(
        _workspace=SimpleNamespace(is_closed=False, post_booking=failed_post),
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
        _refresh_kr_monitoring=lambda: calls.append("KR"),
        _refresh_accounts=lambda: calls.append("accounts"),
        _refresh_journal=lambda: calls.append("journal"),
        _refresh_balance_sheet=lambda: calls.append("balance sheet"),
    )

    MainWindow._post_booking(successful_window, object())

    assert calls == ["posted", "KR", "accounts", "journal", "balance sheet"]
