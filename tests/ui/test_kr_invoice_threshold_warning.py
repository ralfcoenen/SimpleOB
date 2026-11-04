from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from simpleob.amount_input import format_german_amount
from simpleob.domain.kr_monitoring import KrCalendarYearTotals, KrMonitoringSummary
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.vat_booking_frame import VatBookingFrame

_APP = QApplication.instance() or QApplication([])


def _summary(
    *,
    year: int = 2026,
    balance: str = "99950.00",
    external_turnover: str = "0.00",
    limit: str = "100000.00",
    activity_start_date: date | None = date(2020, 1, 1),
    waiver_declared: bool = False,
) -> KrMonitoringSummary:
    return KrMonitoringSummary(
        previous_year=KrCalendarYearTotals(
            calendar_year=year - 1,
            customer_payments=Decimal("0.00"),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
        ),
        current_year=KrCalendarYearTotals(
            calendar_year=year,
            customer_payments=Decimal(balance),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
            external_turnover=Decimal(external_turnover),
            limit=Decimal(limit),
        ),
        activity_start_date=activity_start_date,
        waiver_declared=waiver_declared,
    )


def _frame(summary: KrMonitoringSummary) -> VatBookingFrame:
    frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=lambda _booking: None,
        company_id=UUID(int=1),
        kr_summary_provider=lambda: summary,
    )
    frame._invoice_type_box.setCurrentText("Ausgangsrechnung")
    amount_entry = frame._position_rows[0]["amount_entry"]
    amount_entry.setText("100,00")
    return frame


def test_warns_when_forecast_exceeds_limit_and_not_when_equal_or_below(
    monkeypatch,
):
    calls: list[tuple] = []

    def warning(*args):
        calls.append(args)

    monkeypatch.setattr(QMessageBox, "warning", warning)
    frame = _frame(_summary(balance="99925.00", external_turnover="25.00"))
    amount_entry = frame._position_rows[0]["amount_entry"]
    try:
        amount_entry.editingFinished.emit()
        assert len(calls) == 1
        _parent, title, message, button = calls[0]
        assert title == "Umsatzgrenze voraussichtlich überschritten"
        assert "Bisheriger Umsatz: 99.950,00 €" in message
        assert "Neue Ausgangsrechnung: 100,00 €" in message
        assert "Prognostizierter Umsatz: 100.050,00 €" in message
        assert "Maßgebliche Grenze: 100.000,00 €" in message
        assert button == QMessageBox.StandardButton.Ok
    finally:
        frame.close()

    for balance in ("99900.00", "99800.00"):
        calls.clear()
        frame = _frame(_summary(balance=balance))
        amount_entry = frame._position_rows[0]["amount_entry"]
        try:
            amount_entry.editingFinished.emit()
            assert calls == []
        finally:
            frame.close()


@pytest.mark.parametrize(
    ("year", "start_year", "balance", "limit"),
    (
        (2026, 2026, "24950.00", "25000.00"),
        (2027, 2026, "99950.00", "100000.00"),
    ),
)
def test_uses_startup_year_and_following_year_limits(
    year, start_year, balance, limit, monkeypatch
):
    calls: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: calls.append(args),
    )
    frame = _frame(
        _summary(
            year=year,
            balance=balance,
            limit=limit,
            activity_start_date=date(start_year, 5, 1),
        ),
    )
    amount_entry = frame._position_rows[0]["amount_entry"]
    try:
        amount_entry.editingFinished.emit()
        assert len(calls) == 1
        assert (
            f"Maßgebliche Grenze: {format_german_amount(Decimal(limit))} €"
            in calls[0][2]
        )
    finally:
        frame.close()


def test_waiver_suppresses_warning_and_identical_blur_is_not_repeated(
    monkeypatch,
):
    calls: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: calls.append(args),
    )
    frame = _frame(_summary(waiver_declared=True))
    amount_entry = frame._position_rows[0]["amount_entry"]
    try:
        amount_entry.editingFinished.emit()
        assert calls == []
    finally:
        frame.close()

    frame = _frame(_summary())
    amount_entry = frame._position_rows[0]["amount_entry"]
    try:
        amount_entry.editingFinished.emit()
        amount_entry.editingFinished.emit()
        assert len(calls) == 1

        amount_entry.setText("200,00")
        amount_entry.editingFinished.emit()
        assert len(calls) == 2

        frame._clear()
        amount_entry.setText("200,00")
        amount_entry.editingFinished.emit()
        assert len(calls) == 3

        frame._company_id = UUID(int=2)
        amount_entry.editingFinished.emit()
        assert len(calls) == 4
    finally:
        frame.close()


@pytest.mark.parametrize("tax_rate", ("0 %", "7 %", "19 %"))
def test_gross_invoice_amount_is_not_increased_by_vat_rate(tax_rate, monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: calls.append(args),
    )
    frame = _frame(_summary(balance="99950.00"))
    amount_entry = frame._position_rows[0]["amount_entry"]
    try:
        frame._position_rows[0]["tax_rate_box"].setCurrentText(tax_rate)
        amount_entry.editingFinished.emit()
        assert len(calls) == 1
        assert "Neue Ausgangsrechnung: 100,00 €" in calls[0][2]
        assert "Prognostizierter Umsatz: 100.050,00 €" in calls[0][2]
    finally:
        frame.close()
