from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QApplication

from simpleob.domain.kr_monitoring import KrCalendarYearTotals, KrMonitoringSummary
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.vat_booking_frame import VatBookingFrame


def test_vat_booking_frame_shows_two_calendar_years_and_scope_warning():
    app = QApplication.instance() or QApplication([])
    summary = KrMonitoringSummary(
        previous_year=KrCalendarYearTotals(
            calendar_year=2025,
            customer_payments=Decimal("25000.00"),
            customer_refunds=Decimal("100.00"),
            has_direct_revenue_bookings=False,
            external_turnover=Decimal("50.00"),
            limit=Decimal("25000.00"),
        ),
        current_year=KrCalendarYearTotals(
            calendar_year=2026,
            customer_payments=Decimal("1200.00"),
            customer_refunds=Decimal("200.00"),
            has_direct_revenue_bookings=True,
            external_turnover=Decimal("75.00"),
            limit=Decimal("100000.00"),
        ),
        activity_start_date=date(2020, 2, 1),
    )
    frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=lambda _booking: None,
        kr_summary_provider=lambda: summary,
    )
    try:
        assert frame._kr_previous_year_label.text() == "Vorjahr 2025"
        assert frame._kr_current_year_label.text() == "Laufendes Jahr 2026"
        assert frame._kr_value_labels["payments"][0].text() == "25.000,00 €"
        assert frame._kr_value_labels["refunds"][1].text() == "200,00 €"
        assert frame._kr_value_labels["external"][0].text() == "50,00 €"
        assert frame._kr_value_labels["balance"][0].text() == "24.950,00 €"
        assert frame._kr_value_labels["limit"][0].text() == "25.000,00 €"
        assert frame._kr_value_labels["limit"][1].text() == "100.000,00 €"
        assert not frame._kr_direct_revenue_warning.isHidden()
        assert "auf Ziel erfasst werden" in frame._kr_scope_note.text()
        assert "keine vollständige steuerrechtliche Prüfung" in frame._kr_scope_note.text()
        assert frame._kr_activity_start_warning.isHidden()
    finally:
        frame.close()
        app.processEvents()


def test_waiver_hides_kr_box_and_missing_activity_date_shows_hint():
    app = QApplication.instance() or QApplication([])
    summary = KrMonitoringSummary(
        previous_year=KrCalendarYearTotals(
            calendar_year=2025,
            customer_payments=Decimal("0.00"),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
        ),
        current_year=KrCalendarYearTotals(
            calendar_year=2026,
            customer_payments=Decimal("0.00"),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
        ),
        waiver_declared=True,
    )
    frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=lambda _booking: None,
        kr_summary_provider=lambda: summary,
    )
    try:
        assert frame._kr_summary_box.isHidden()

        summary = KrMonitoringSummary(
            previous_year=KrCalendarYearTotals(
                calendar_year=2025,
                customer_payments=Decimal("0.00"),
                customer_refunds=Decimal("0.00"),
                has_direct_revenue_bookings=False,
            ),
            current_year=KrCalendarYearTotals(
                calendar_year=2026,
                customer_payments=Decimal("0.00"),
                customer_refunds=Decimal("0.00"),
                has_direct_revenue_bookings=False,
            ),
        )
        frame._kr_summary_provider = lambda: summary
        frame.refresh_kr_summary()
        assert not frame._kr_summary_box.isHidden()
        assert not frame._kr_activity_start_warning.isHidden()
    finally:
        frame.close()
        app.processEvents()


def test_kr_query_failure_does_not_prevent_booking_frame_creation():
    app = QApplication.instance() or QApplication([])

    def unavailable_summary():
        raise RuntimeError("database unavailable")

    frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=lambda _booking: None,
        kr_summary_provider=unavailable_summary,
    )
    try:
        assert frame._kr_error_label.text() == (
            "Die Umsatzüberwachung ist derzeit nicht verfügbar."
        )
        assert not frame._kr_error_label.isHidden()
        assert frame._invoice_type_box.isEnabled()
    finally:
        frame.close()
        app.processEvents()
