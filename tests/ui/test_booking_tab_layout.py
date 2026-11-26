from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QWidget,
)

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.main_window import MainWindow


def _booking_window() -> MainWindow:
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._account_editing_mode = False
    window._booking_tab = QWidget(window)
    window._opening_balance_account_number = "9000"
    window._closing_accounts = SimpleNamespace(
        income_summary_account="9998",
        profit_account="9999",
        loss_account="9997",
    )
    window._accounts = (
        Account(
            TemplateAccount("10000", "Muster GmbH", AccountType.ASSET),
            person_account_role=PersonAccountRole.DEBITOR,
        ),
        Account(
            TemplateAccount("1576", "Vorsteuer 19 %", AccountType.ASSET),
        ),
        Account(
            TemplateAccount("70000", "Muster GmbH", AccountType.LIABILITY),
            person_account_role=PersonAccountRole.KREDITOR,
        ),
        Account(
            TemplateAccount("1776", "Umsatzsteuer 19 %", AccountType.LIABILITY),
        ),
    )
    window._vat_accounts = VatAccounts("1576", "1571", "1776", "1771")
    window._chart_of_accounts = SimpleNamespace(account_mapping_rules=())
    window._context = SimpleNamespace(company=SimpleNamespace(company_id=uuid4()))
    window._workspace = SimpleNamespace(is_open=True)
    window._person_account_repository = None
    window._opening_balance_button = QPushButton()
    window._create_booking_tab()
    window.setCentralWidget(window._booking_tab)
    return window


def _assert_label_close_to_field(frame: QWidget, field: QWidget) -> None:
    labels = [
        label
        for label in frame.findChildren(QLabel)
        if label.buddy() is field
    ]
    assert len(labels) == 1
    label = labels[0]
    label_right = label.mapTo(frame, label.rect().topLeft()).x() + label.width()
    field_left = field.mapTo(frame, field.rect().topLeft()).x()
    assert 0 <= field_left - label_right <= 12


def test_booking_tab_only_exposes_general_booking_and_keeps_compact_layout():
    app = QApplication.instance() or QApplication([])
    window = _booking_window()
    window.resize(1200, 760)
    window.show()
    app.processEvents()

    groups = {group.title() for group in window.findChildren(QGroupBox)}
    assert window._bank_import_button.text() == "Bankumsätze importieren"
    assert window._bank_import_button.isVisible()
    assert "Neue Buchung" in groups
    assert "OP-Verwaltung" not in groups
    assert not any("Umsatzüberwachung" in title for title in groups)
    assert not hasattr(window, "_booking_columns_splitter")
    assert window._booking_frame.isVisible()

    scroll_area = window.findChild(QScrollArea)
    assert scroll_area is not None
    assert scroll_area.widgetResizable()

    window.resize(1100, 700)
    app.processEvents()
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


def test_general_booking_account_choices_include_person_and_tax_accounts():
    app = QApplication.instance() or QApplication([])
    window = _booking_window()
    account_names = set(window._booking_frame._account_display_names)

    assert any("10000" in name and "Debitor" in name for name in account_names)
    assert any("70000" in name and "Kreditor" in name for name in account_names)
    assert any("1576" in name for name in account_names)
    assert any("1776" in name for name in account_names)

    window.close()
    app.processEvents()


def test_booking_tab_open_and_successful_transfer_focus_and_select_date():
    app = QApplication.instance() or QApplication([])
    window = _booking_window()
    notebook = QTabWidget()
    notebook.addTab(QWidget(), "Andere Ansicht")
    notebook.addTab(window._booking_tab, "Buchen")
    window._notebook = notebook
    notebook.currentChanged.connect(window._focus_booking_date_when_opened)
    window.setCentralWidget(notebook)
    window.show()
    notebook.setCurrentIndex(1)
    app.processEvents()

    frame = window._booking_frame
    date_entry = frame._booking_date_entry
    assert app.focusWidget() is date_entry
    assert date_entry.selectedText() == date_entry.text()

    date_entry.setText("24.11.2026")
    frame._description_entry.setText("Testbuchung")
    debit_row = frame._rows[0]
    debit_row.account_entry.setText("10000")
    debit_row.debit_entry.setText("100")
    credit_row = frame._rows[1]
    credit_row.account_entry.setText("70000")
    credit_row.credit_entry.setText("100")
    frame._on_booking_created = lambda *_args: None
    frame._create_booking()
    app.processEvents()

    assert app.focusWidget() is date_entry
    assert date_entry.selectedText() == date_entry.text()

    window.close()


def test_account_completer_popup_expands_for_long_names_within_screen():
    app = QApplication.instance() or QApplication([])
    window = _booking_window()
    frame = window._booking_frame
    long_name = ("Kontobezeichnung mit ausführlicher Beschreibung " * 3).strip()
    long_account = Account(
        TemplateAccount("99999", long_name, AccountType.ASSET),
    )
    frame.update_accounts(
        accounts=frame._accounts + (long_account,),
        equity_contribution_account_numbers=frozenset(),
    )
    frame._rows[0].debit_entry.setText("1")
    frame._rows[1].credit_entry.setText("1")
    window.resize(760, 520)
    window.show()
    app.processEvents()

    for row in frame._rows:
        assert row.completer.popup().minimumWidth() > 450

    row = frame._rows[0]
    row.account_entry.setFocus()
    QTest.keyClicks(row.account_entry, "999")
    app.processEvents()

    popup = row.completer.popup()
    screen_geometry = row.account_entry.screen().availableGeometry()
    popup_geometry = popup.frameGeometry()
    assert popup.isVisible()
    assert popup_geometry.width() > 450
    assert popup.width() > row.account_entry.width()
    assert popup_geometry.left() >= screen_geometry.left()
    assert popup_geometry.right() <= screen_geometry.right()
    assert popup_geometry.top() >= screen_geometry.top()
    assert popup_geometry.bottom() <= screen_geometry.bottom()

    window.close()
