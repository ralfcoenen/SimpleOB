from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from simpleob.domain.kr_monitoring import KrCalendarYearTotals, KrMonitoringSummary
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.main_window import MainWindow
from simpleob.ui_qt.vat_booking_frame import ResponsiveBookingSplitter


def _assert_label_close_to_field(frame: QWidget, field: QWidget) -> None:
    labels = [
        label
        for label in frame.findChildren(QLabel)
        if label.buddy() is field
    ]
    assert len(labels) == 1
    label = labels[0]
    label_right = label.mapTo(frame, QPoint()).x() + label.width()
    field_left = field.mapTo(frame, QPoint()).x()
    assert 0 <= field_left - label_right <= 12


def _booking_window(*, enable_invoice_actions: bool = False) -> MainWindow:
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._booking_tab = QWidget(window)
    for attribute in (
        "_open_item_payment_service",
        "_open_item_offset_service",
        "_open_item_credit_refund_service",
        "_open_item_credit_refund_reversal_service",
        "_payment_allocation_correction_service",
        "_receivable_invoice_posting_service",
        "_payable_invoice_posting_service",
        "_credit_note_posting_service",
    ):
        setattr(window, attribute, None)
    if enable_invoice_actions:
        for attribute in (
            "_receivable_invoice_posting_service",
            "_payable_invoice_posting_service",
            "_credit_note_posting_service",
        ):
            setattr(window, attribute, object())

    window._business_partner_repository = None
    window._opening_balance_account_number = "9000"
    window._closing_accounts = SimpleNamespace(
        income_summary_account="9998",
        profit_account="9999",
        loss_account="9997",
    )
    window._accounts = ()
    window._vat_accounts = VatAccounts("1576", "1571", "1776", "1771")
    window._chart_of_accounts = SimpleNamespace(account_mapping_rules=())
    window._context = SimpleNamespace(
        company=SimpleNamespace(company_id=uuid4())
    )
    window._workspace = SimpleNamespace(is_open=True)
    window._kr_monitoring_service = None
    window._opening_balance_button = QPushButton()
    window._create_booking_tab()
    window.setCentralWidget(window._booking_tab)
    return window


def test_booking_tab_groups_op_actions_and_fits_reduced_width():
    app = QApplication.instance() or QApplication([])
    window = _booking_window()
    window.resize(1200, 760)
    window.show()
    app.processEvents()

    groups = {
        group.title(): group for group in window.findChildren(QGroupBox)
    }
    assert "OP-Verwaltung" in groups
    assert "Neue Buchung" in groups

    action_buttons = (
        window._payment_button,
        window._offset_button,
        window._credit_refund_button,
        window._credit_refund_reversal_button,
        window._payment_correction_button,
    )
    assert all(
        button.sizePolicy().horizontalPolicy()
        == QSizePolicy.Policy.Maximum
        for button in action_buttons
    )

    scroll_area = window.findChild(QScrollArea)
    assert scroll_area is not None
    assert scroll_area.widgetResizable()

    window.resize(1100, 700)
    app.processEvents()
    op_group = groups["OP-Verwaltung"]
    assert op_group.isVisible()
    assert op_group.width() > window._booking_columns_splitter.width()
    assert all(button.width() >= button.sizeHint().width() for button in action_buttons)
    assert all(button.width() < op_group.width() for button in action_buttons)

    date_geometry = window._booking_frame._booking_date_entry.geometry()
    voucher_geometry = window._booking_frame._voucher_no_entry.geometry()
    assert date_geometry.y() == voucher_geometry.y()
    assert date_geometry.right() < voucher_geometry.left()
    assert window._booking_frame._booking_table.minimumHeight() < 220
    window.resize(1600, 700)
    app.processEvents()
    _assert_label_close_to_field(
        window._booking_frame,
        window._booking_frame._booking_date_entry,
    )
    _assert_label_close_to_field(
        window._booking_frame,
        window._booking_frame._voucher_no_entry,
    )

    window.close()
    app.processEvents()


def test_invoice_booking_layout_switches_related_fields_without_clipping():
    app = QApplication.instance() or QApplication([])
    window = _booking_window(enable_invoice_actions=True)
    window.resize(1100, 700)
    window.show()
    app.processEvents()

    window._booking_mode_box.setCurrentText("Rechnung mit Umsatzsteuer")
    app.processEvents()
    frame = window._vat_booking_frame
    summary = KrMonitoringSummary(
        previous_year=KrCalendarYearTotals(
            calendar_year=2025,
            customer_payments=Decimal("25000.00"),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
            external_turnover=Decimal("0.00"),
            limit=Decimal("25000.00"),
        ),
        current_year=KrCalendarYearTotals(
            calendar_year=2026,
            customer_payments=Decimal("0.00"),
            customer_refunds=Decimal("0.00"),
            has_direct_revenue_bookings=False,
            external_turnover=Decimal("0.00"),
            limit=Decimal("100000.00"),
        ),
        activity_start_date=date(2020, 1, 1),
    )
    frame._kr_summary_provider = lambda: summary
    frame.refresh_kr_summary()
    splitter = window._booking_columns_splitter
    assert isinstance(splitter, ResponsiveBookingSplitter)
    scroll_area = window.findChild(QScrollArea)
    assert frame.isVisible()
    assert not window._booking_frame.isVisible()
    assert scroll_area is not None
    assert scroll_area.horizontalScrollBar().maximum() == 0
    assert frame._on_account.isVisible()
    assert not frame._partner_box.isVisible()
    assert not frame._due_date_entry.isVisible()
    assert not frame._original_invoice_number_entry.isVisible()
    window.resize(1600, 700)
    app.processEvents()
    assert splitter.orientation().name == "Horizontal"
    left_width, right_width = splitter.sizes()
    assert 0.55 <= left_width / (left_width + right_width) <= 0.65
    assert frame.kr_summary_widget.isVisible()
    _assert_label_close_to_field(frame, frame._invoice_type_box)
    _assert_label_close_to_field(frame, frame._booking_date_entry)
    _assert_label_close_to_field(frame, frame._voucher_no_entry)
    assert scroll_area.horizontalScrollBar().maximum() == 0

    frame._on_account.setChecked(True)
    app.processEvents()
    assert frame._partner_box.isVisible()
    assert frame._due_date_entry.isVisible()
    assert not frame._original_invoice_number_entry.isVisible()
    _assert_label_close_to_field(frame, frame._on_account)
    _assert_label_close_to_field(frame, frame._partner_box)
    _assert_label_close_to_field(frame, frame._due_date_entry)

    frame._invoice_type_box.setCurrentText("Ausgangsrechnung")
    app.processEvents()
    assert frame._on_account.isVisible()
    assert not frame._on_account.isChecked()
    assert not frame._due_date_entry.isVisible()

    frame._invoice_type_box.setCurrentText("Kundengutschrift")
    app.processEvents()
    assert not frame._on_account.isVisible()
    assert frame._partner_box.isVisible()
    assert frame._original_invoice_number_entry.isVisible()
    assert frame._original_invoice_number_label.isVisible()
    assert not frame._due_date_label.isVisible()
    _assert_label_close_to_field(
        frame,
        frame._original_invoice_number_entry,
    )

    frame._invoice_type_box.setCurrentText("Lieferantengutschrift")
    app.processEvents()
    assert frame._partner_label.text() == "Lieferant"
    assert frame._original_invoice_number_entry.isVisible()

    window.resize(800, 700)
    app.processEvents()
    assert splitter.orientation().name == "Vertical"
    assert scroll_area.horizontalScrollBar().maximum() == 0
    assert frame.kr_summary_widget.isVisible()
    frame._invoice_type_box.setCurrentText("Ausgangsrechnung")
    app.processEvents()
    assert frame._on_account.isVisible()
    for widget in (
        window._booking_mode_box,
        frame._invoice_type_box,
        frame._booking_date_entry,
        frame._voucher_no_entry,
        frame._booking_button,
        frame.kr_summary_widget,
    ):
        right = widget.mapTo(scroll_area.viewport(), QPoint()).x() + widget.width()
        assert right <= scroll_area.viewport().width()
    assert scroll_area.horizontalScrollBar().maximum() == 0

    window._booking_mode_box.setCurrentText("Einfache Buchung")
    app.processEvents()
    assert window._booking_frame.isVisible()
    assert not frame.isVisible()

    window.close()
    app.processEvents()
