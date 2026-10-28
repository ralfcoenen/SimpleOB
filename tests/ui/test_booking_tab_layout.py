from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.main_window import MainWindow


def _booking_window() -> MainWindow:
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
    assert all(button.width() >= button.sizeHint().width() for button in action_buttons)
    assert all(button.width() < op_group.width() for button in action_buttons)

    window.close()
    app.processEvents()
