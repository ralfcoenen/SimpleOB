from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.bank_booking_proposal import CounterBookingLineProposal
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.bank_transaction_import_dialog import (
    BankTransactionImportDialog,
    CounterBookingLinesDialog,
)
from simpleob.ui_qt.booking_frame import BookingFrame
from simpleob.ui_qt.input_focus import SelectAllOnFocusFilter
from simpleob.ui_qt.main_window import MainWindow

_APP = QApplication.instance() or QApplication([])


def _accounts():
    return (
        Account(TemplateAccount("1200", "Bank", AccountType.ASSET)),
        Account(TemplateAccount("4930", "Bürobedarf", AccountType.EXPENSE)),
        Account(TemplateAccount("1576", "Abziehbare Vorsteuer", AccountType.ASSET)),
        Account(TemplateAccount("1776", "Umsatzsteuer", AccountType.LIABILITY)),
        Account(
            TemplateAccount("10000", "Muster GmbH", AccountType.ASSET),
            person_account_role=PersonAccountRole.DEBITOR,
        ),
    )


def _csv(tmp_path, contents=None):
    path = tmp_path / "umsatz.csv"
    path.write_text(
        contents
        or (
            "Transaction ID;Status;Settlement date (local);Counterparty name;Reference;"
            "Total amount (incl. VAT);Currency\n"
            "TEST-001;completed;16.11.2026;Bürobedarf GmbH;Büromaterial;-119,00;EUR\n"
        ),
        encoding="utf-8",
    )
    return path


def _dialog(*, duplicate_lookup=lambda _transaction: None, post_proposal=lambda *_args, **_kwargs: None):
    parent = QWidget()
    booking_frame = BookingFrame(
        parent=parent,
        accounts=_accounts(),
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=lambda *_args: None,
    )
    dialog = BankTransactionImportDialog(
        parent=parent,
        accounts=_accounts(),
        amount_entry_factory=booking_frame.create_amount_entry,
        bank_account_numbers=frozenset({"1200"}),
        duplicate_lookup=duplicate_lookup,
        post_proposal=post_proposal,
    )
    dialog._test_parent = parent
    dialog._test_booking_frame = booking_frame
    return dialog


def _prepare_valid_row(dialog, path):
    dialog.load_csv(path)
    dialog._bank_account_combo.setCurrentIndex(1)
    contra = dialog._counter_combos[0]
    contra.setCurrentIndex(contra.findData("10000"))
    return dialog._checkbox(0)


def test_import_dialog_loads_synthetic_csv_and_edits_proposal(tmp_path):
    dialog = _dialog()
    dialog.load_csv(_csv(tmp_path))

    assert dialog.transactions[0].amount == Decimal("-119.00")
    assert dialog._table.rowCount() == 1
    assert dialog._bank_account_combo.itemData(1) == "1200"
    assert dialog._checkbox(0).isEnabled() is False

    dialog._bank_account_combo.setCurrentIndex(1)
    contra = dialog._counter_combos[0]
    contra.setCurrentIndex(contra.findData("10000"))
    dialog._table.cellWidget(0, 6).setText("Geänderter Buchungstext")
    dialog._table.cellWidget(0, 1).setDate(QDate(2026, 11, 18))
    proposal = dialog._proposals[0]

    assert proposal.bank_account_number == "1200"
    assert proposal.counter_lines[0].account_number == "10000"
    assert proposal.description == "Geänderter Buchungstext"
    assert proposal.booking_date == date(2026, 11, 18)
    assert proposal.is_valid
    assert dialog._checkbox(0).isEnabled()
    dialog.close()


def test_import_dialog_disables_persistently_imported_transaction(tmp_path):
    dialog = _dialog(duplicate_lookup=lambda _transaction: uuid4())
    dialog.load_csv(_csv(tmp_path))

    assert not dialog._checkbox(0).isEnabled()
    assert "Bereits übernommen" in dialog._table.item(0, 7).text()
    assert "0 buchbar" in dialog._summary.text()
    dialog.close()


def test_import_dialog_requires_confirmation_and_reports_success(tmp_path, monkeypatch):
    posted = []
    booking = SimpleNamespace(booking_id=uuid4())
    dialog = _dialog(post_proposal=lambda proposal, **kwargs: posted.append((proposal, kwargs)) or booking)
    checkbox = _prepare_valid_row(dialog, _csv(tmp_path))
    checkbox.setChecked(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )
    dialog._confirm_selected()
    assert posted == []

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: None)
    dialog._confirm_selected()

    assert len(posted) == 1
    assert posted[0][1] == {"confirmed": True}
    assert dialog.success_count == 1
    assert "Übernommen" in dialog._table.item(0, 7).text()
    dialog.close()


def test_import_dialog_displays_parser_and_row_validation_errors(tmp_path):
    dialog = _dialog()
    dialog.load_csv(
        _csv(
            tmp_path,
            "Transaction ID;Status;Settlement date (local);Counterparty name;Reference;"
            "Total amount (incl. VAT);Currency\n"
            ";completed;31.02.2026;Partner;Text;1,00;EUR\n",
        )
    )
    assert "Zeile 2" in dialog._error_label.text()
    assert dialog._table.rowCount() == 0
    dialog.close()

    dialog = _dialog()
    dialog.load_csv(_csv(tmp_path, "Transaction ID;Status\nX;pending\n"))
    assert "Fehlende Pflichtspalten" in dialog._error_label.text()
    assert not dialog._post_button.isEnabled()
    dialog.close()


def test_non_settled_transaction_cannot_be_selected(tmp_path):
    dialog = _dialog()
    dialog.load_csv(
        _csv(
            tmp_path,
            "Transaction ID;Status;Settlement date (local);Counterparty name;Reference;"
            "Total amount (incl. VAT);Currency\n"
            "TEST-002;pending;17.11.2026;Muster GmbH;Referenz;1190,00;EUR\n",
        )
    )
    assert dialog._checkbox(0) is not None
    assert not dialog._checkbox(0).isEnabled()
    assert "Nicht abgewickelt" in dialog._table.item(0, 7).text()
    dialog.close()


def test_main_window_opens_separate_import_dialog(monkeypatch):
    calls = []

    class DialogStub:
        success_count = 0

        def __init__(self, **kwargs):
            calls.append(kwargs)

        def exec(self):
            calls.append("exec")

    monkeypatch.setattr(main_window_module, "BankTransactionImportDialog", DialogStub)
    workspace = SimpleNamespace(
        bank_account_numbers=lambda: frozenset({"1200"}),
        bank_transaction_booking_id=lambda **_kwargs: None,
        post_bank_booking_proposal=lambda *_args, **_kwargs: None,
        journal=SimpleNamespace(bookings=()),
    )
    window = SimpleNamespace(
        _workspace=workspace,
        _booking_frame=SimpleNamespace(
            _accounts=_accounts(),
            create_amount_entry=lambda: QLineEdit(),
        ),
        _post_bank_booking_proposal=lambda *_args, **_kwargs: None,
    )

    MainWindow._open_bank_import_dialog(window)

    assert calls[-1] == "exec"
    assert calls[0]["bank_account_numbers"] == frozenset({"1200"})


def _counter_dialog(lines):
    parent = QWidget()
    booking_frame = BookingFrame(
        parent=parent,
        accounts=_accounts(),
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=lambda *_args: None,
    )
    dialog = CounterBookingLinesDialog(
        parent=parent,
        bank_amount=Decimal("119.00"),
        accounts=_accounts(),
        lines=lines,
        amount_entry_factory=booking_frame.create_amount_entry,
    )
    dialog._test_parent = parent
    dialog._test_booking_frame = booking_frame
    return dialog


def test_counter_line_dialog_adds_and_removes_rows():
    dialog = _counter_dialog(
        (CounterBookingLineProposal("4930", Decimal("119.00")),)
    )

    dialog._add_line_button.click()
    assert dialog._table.rowCount() == 2
    assert dialog._rows[1]["amount"].text() == "0,00"
    dialog._remove_line(dialog._rows[1])
    assert dialog._table.rowCount() == 1
    assert dialog._rows[0]["amount"].text() == "119,00"
    assert dialog._rows[0]["amount"].property("amountNormalized") is True
    dialog.close()


def test_counter_line_dialog_edits_account_amount_and_accepts_split():
    dialog = _counter_dialog(
        (CounterBookingLineProposal("4930", Decimal("119.00")),)
    )
    first = dialog._rows[0]
    first["account"].setCurrentIndex(first["account"].findData("10000"))
    first["amount"].setText("10000")
    assert dialog._current_total() == Decimal("100.00")
    assert "Differenz: 19,00 €" in dialog._sum_label.text()
    first["amount"].editingFinished.emit()
    assert first["amount"].text() == "100,00"
    dialog._add_line_button.click()
    second = dialog._rows[1]
    second["account"].setCurrentIndex(second["account"].findData("1576"))
    second["amount"].setText("1900")
    assert dialog._current_total() == Decimal("119.00")
    assert "Differenz: 0,00 €" in dialog._sum_label.text()
    second["amount"].editingFinished.emit()
    assert second["amount"].text() == "19,00"

    assert dialog._validation_label.text() == ""
    assert dialog._buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog._accept_if_valid()
    assert dialog.counter_lines == (
        CounterBookingLineProposal("10000", Decimal("100.00")),
        CounterBookingLineProposal("1576", Decimal("19.00")),
    )
    dialog.close()


def test_counter_line_dialog_blocks_unbalanced_amount_and_keeps_input():
    dialog = _counter_dialog(
        (CounterBookingLineProposal("4930", Decimal("118.00")),)
    )
    assert "Es fehlen 1,00 €" in dialog._validation_label.text()
    assert not dialog._buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()

    dialog._rows[0]["amount"].setText("11900")
    assert "Differenz: 0,00 €" in dialog._sum_label.text()
    dialog._rows[0]["amount"].editingFinished.emit()
    assert dialog._rows[0]["amount"].text() == "119,00"
    assert dialog._validation_label.text() == ""
    dialog._accept_if_valid()
    assert dialog.counter_lines[0].amount == Decimal("119.00")
    dialog.close()


def test_counter_amount_edit_replaces_selected_formatted_value_like_booking_mask():
    event_filter = SelectAllOnFocusFilter(_APP)
    _APP.installEventFilter(event_filter)
    dialog = _counter_dialog(
        (CounterBookingLineProposal("4930", Decimal("119.00")),)
    )
    dialog.show()
    _APP.processEvents()
    amount_edit = dialog._rows[0]["amount"]
    assert amount_edit.text() == "119,00"

    dialog._add_line_button.setFocus()
    _APP.processEvents()
    amount_edit.setFocus()
    _APP.processEvents()
    assert amount_edit.selectedText() == "119,00"
    QTest.keyClicks(amount_edit, "11900")
    assert amount_edit.text() == "11900"
    assert dialog._current_total() == Decimal("119.00")
    amount_edit.editingFinished.emit()
    assert amount_edit.text() == "119,00"

    dialog._add_line_button.setFocus()
    _APP.processEvents()
    amount_edit.setFocus()
    _APP.processEvents()
    assert amount_edit.selectedText() == "119,00"
    QTest.keyClicks(amount_edit, "1900")
    assert amount_edit.text() == "1900"
    assert dialog._current_total() == Decimal("19.00")

    amount_edit.editingFinished.emit()
    assert amount_edit.text() == "19,00"
    assert amount_edit.property("amountNormalized") is True
    assert dialog._current_total() == Decimal("19.00")

    dialog.close()
    _APP.removeEventFilter(event_filter)
    event_filter.deleteLater()


def test_counter_line_dialog_sizes_table_and_controls_for_available_screen():
    dialog = _counter_dialog(
        (CounterBookingLineProposal("4930", Decimal("119.00")),)
    )
    dialog.show()
    _APP.processEvents()

    account_combo = dialog._rows[0]["account"]
    amount_edit = dialog._rows[0]["amount"]
    remove_button = dialog._rows[0]["remove"]
    assert dialog.width() >= dialog.minimumWidth()
    assert dialog.height() >= dialog.minimumHeight()
    assert dialog.isSizeGripEnabled()
    assert account_combo.isVisible() and account_combo.width() >= 300
    assert amount_edit.isVisible() and amount_edit.width() >= 130
    assert remove_button.isVisible() and remove_button.width() >= 100
    assert dialog._sum_label.isVisible()
    assert dialog._buttons.isVisible()

    required_table_width = sum(
        dialog._table.columnWidth(column) for column in range(dialog._table.columnCount())
    )
    if dialog._table.viewport().width() < required_table_width:
        assert dialog._table.horizontalScrollBar().maximum() > 0
    else:
        assert dialog._table.horizontalScrollBar().maximum() == 0
    dialog.close()


def test_visible_import_row_opens_splitter_and_adds_counter_line(tmp_path):
    dialog = _dialog()
    dialog.load_csv(_csv(tmp_path))
    dialog.show()
    _APP.processEvents()

    assert dialog._table.rowCount() == 1
    cell = dialog._table.cellWidget(0, 5)
    combo = cell.findChild(QComboBox)
    split_button = next(
        button
        for button in cell.findChildren(QPushButton)
        if button.text() == "Aufteilen …"
    )
    assert combo is not None
    assert combo.isVisible() and combo.isEnabled()
    assert combo.height() >= 20
    assert split_button.isVisible() and split_button.isEnabled()
    assert split_button.height() >= 20
    assert dialog._table.rowHeight(0) >= 70

    QTest.mouseClick(combo, Qt.MouseButton.LeftButton)
    _APP.processEvents()
    assert combo.view().isVisible()
    QTest.keyClick(combo, Qt.Key.Key_Escape)

    result = []

    def add_second_line_and_cancel():
        splitter = QApplication.activeModalWidget()
        try:
            add_button = next(
                button
                for button in splitter.findChildren(QPushButton)
                if button.text() == "Gegenbuchungszeile hinzufügen"
            )
            add_button.click()
            result.append(splitter._table.rowCount())
            splitter._buttons.button(QDialogButtonBox.StandardButton.Cancel).click()
        except Exception as exc:  # captured in the Qt callback and asserted below
            result.append(exc)

    QTimer.singleShot(0, add_second_line_and_cancel)
    QTest.mouseClick(split_button, Qt.MouseButton.LeftButton)
    _APP.processEvents()

    assert result == [2]
    assert len(dialog._proposals[0].counter_lines) == 1
    dialog.close()
