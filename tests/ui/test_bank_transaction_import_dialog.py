from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QWidget,
    QWizard,
)

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.bank_booking_proposal import CounterBookingLineProposal
from simpleob.domain.bank_transaction import BankImportSource
from simpleob.domain.csv_import_profile import qonto_compatibility_profile
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.services.csv_import_profile_store import CsvImportProfileStore
from simpleob.ui_qt import bank_transaction_import_dialog as import_dialog_module
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.bank_transaction_import_dialog import (
    BankTransactionImportDialog,
    CounterBookingLinesDialog,
)
from simpleob.ui_qt.booking_frame import BookingFrame
from simpleob.ui_qt.csv_import_profile_dialog import CsvImportProfileDialog
from simpleob.ui_qt.input_focus import SelectAllOnFocusFilter
from simpleob.ui_qt.main_window import MainWindow

_APP = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_profiles(tmp_path, monkeypatch):
    store = CsvImportProfileStore(tmp_path / "profiles.json")
    monkeypatch.setattr(import_dialog_module, "CsvImportProfileStore", lambda: store)
    return store


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
    assert dialog._raw_table.rowCount() == 1
    assert dialog._raw_table.item(0, 0).text() == "2"
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

        def start_import_assistant(self):
            calls.append("assistant")
            return True

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

    assert calls[-2:] == ["assistant", "exec"]
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


def test_profile_selection_invalidates_preview_and_reuses_booking_flow(tmp_path, isolated_profiles, monkeypatch):
    base = qonto_compatibility_profile()
    other = replace(base, profile_id=uuid4(), name="Andere Richtung", import_source=BankImportSource("other.bank"), amount=replace(base.amount, positive_means="outflow"))
    isolated_profiles.save((base, other))
    posted = []
    dialog = _dialog(post_proposal=lambda proposal, **kw: posted.append((proposal, kw)) or SimpleNamespace(booking_id=uuid4()))
    path = _csv(tmp_path)
    _prepare_valid_row(dialog, path).setChecked(True)
    assert dialog._post_button.isEnabled()
    assert dialog._raw_table.item(0, 1).text() == "TEST-001"
    assert dialog._table.item(0, 8).text() == "TEST-001"
    assert dialog._table.item(0, 9).text() == "completed"
    dialog._profile_combo.setCurrentIndex(1)
    assert not dialog.transactions and not dialog._proposals
    assert dialog._table.rowCount() == dialog._raw_table.rowCount() == 0
    assert not dialog._post_button.isEnabled()
    dialog.load_csv(path)
    assert dialog.transactions[0].amount == Decimal("119.00")
    assert dialog._proposals[0].bank_account_number == "1200"
    dialog._counter_combos[0].setCurrentIndex(dialog._counter_combos[0].findData("4930"))
    dialog._checkbox(0).setChecked(True)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: None)
    dialog._confirm_selected()
    assert posted[0][0].transaction.import_source == other.import_source
    assert posted[0][1] == {"confirmed": True}
    dialog.close()


def _six_csv(tmp_path):
    path = tmp_path / "sechs_umsaetze.csv"
    headers = "Umsatzkennung;Buchungstag;Betrag_EUR;Waehrung;Partner;Verwendungszweck;Bearbeitungsstand;Andere_ID\n"
    rows = [f"U-{n};16.11.2026;{'119,00' if n % 2 else '-19,00'};EUR;Partner {n};Zweck {n};{'vorgemerkt' if n == 6 else 'gebucht'};NEU-{n}\n" for n in range(1, 7)]
    path.write_text(headers + ''.join(rows), encoding="utf-8")
    return path


def _wizard(tmp_path, store, profile=None, path=None, edit_mapping=False, persist_profile=False):
    parent = QWidget()
    wizard = CsvImportProfileDialog(parent=parent, profile=profile, csv_path=path or _six_csv(tmp_path), profile_store=store, edit_mapping=edit_mapping, persist_profile=persist_profile)
    wizard._test_parent = parent
    wizard.show()
    _APP.processEvents()
    return wizard


def _go_to_review(wizard):
    wizard.next()
    assert wizard.currentId() in (1, 2), wizard._error.toPlainText()
    if wizard.currentId() == 1:
        wizard.next()
    assert wizard.currentId() == 2, wizard._error.toPlainText()


def test_wizard_six_transactions_save_and_hand_over_to_existing_booking(tmp_path, isolated_profiles, monkeypatch):
    posted = []
    dialog = _dialog(post_proposal=lambda proposal, **kw: posted.append((proposal, kw)) or SimpleNamespace(booking_id=uuid4()))
    path = _six_csv(tmp_path)
    result = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    def run_assistant():
        wizard = QApplication.activeModalWidget()
        try:
            _go_to_review(wizard)
            assert len(wizard.transactions) == 6
            assert "5 buchbar" in wizard._review_summary.text()
            assert "1 vorgemerkt" in wizard._review_summary.text()
            assert wizard._preview.item(1, 3).text() == "-19,00"
            assert wizard._preview.item(0, 3).text() == "+119,00"
            wizard._preview.setCurrentCell(5, 0)
            assert "U-6" in wizard._detail_heading.text()
            assert wizard._details.item(2, 1).text() == "-19,00"
            assert posted == []
            wizard.next()
            wizard._name.setText("Meine Bank")
            wizard._source.setCurrentText("meine_bank")
            wizard.button(QWizard.WizardButton.FinishButton).click()
            assert wizard.profile is not None
            result.append(True)
        except Exception as exc:
            result.append(exc)
            wizard.reject()

    QTimer.singleShot(0, run_assistant)
    assert dialog.start_import_assistant(csv_path=path)
    assert result == [True]
    assert len(dialog.transactions) == 6
    assert len(dialog._proposals) == 5
    assert not dialog._checkbox(5).isEnabled()
    assert posted == []
    dialog._bank_account_combo.setCurrentIndex(1)
    dialog._counter_combos[0].setCurrentIndex(dialog._counter_combos[0].findData("4930"))
    dialog._checkbox(0).setChecked(True)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: None)
    dialog._confirm_selected()
    assert len(posted) == 1 and posted[0][1] == {"confirmed": True}
    assert posted[0][0].transaction.import_source.value == "meine_bank"
    assert isolated_profiles.load()[-1].name == "Meine Bank"
    dialog.close()


def test_explicit_profile_edit_saves_rename_and_preserves_identity(tmp_path, isolated_profiles):
    profile = qonto_compatibility_profile()
    isolated_profiles.save((profile,))
    dialog = _dialog()
    dialog._csv_path = _csv(tmp_path)
    results = []

    def edit_and_save():
        wizard = QApplication.activeModalWidget()
        try:
            wizard.next()
            assert wizard.currentId() == 1
            wizard.next()
            assert wizard.currentId() == 2
            wizard.next()
            assert wizard.currentId() == 3
            wizard._name.setText("Umbenannt")
            assert not wizard._source.isEnabled()
            wizard.button(QWizard.WizardButton.FinishButton).click()
            assert wizard.profile is not None
            results.append(True)
        except Exception as exc:
            results.append(exc)
            wizard.reject()

    QTimer.singleShot(0, edit_and_save)
    dialog._edit_profile(new=False)
    assert results == [True]
    restored, = isolated_profiles.load()
    assert restored.name == "Umbenannt"
    assert restored.profile_id == profile.profile_id
    assert restored.import_source == profile.import_source
    dialog.close()


def test_mapping_changes_clear_preview_and_back_navigation_keeps_inputs(tmp_path, isolated_profiles):
    wizard = _wizard(tmp_path, isolated_profiles)
    _go_to_review(wizard)
    assert len(wizard.transactions) == 6
    wizard.back()
    wizard._positive.setCurrentIndex(wizard._positive.findData('outflow'))
    assert not wizard.transactions and wizard._preview.rowCount() == 0
    wizard.back()
    wizard.next()
    assert wizard._positive.currentData() == 'outflow'
    wizard.next()
    assert wizard.transactions[0].amount == Decimal('-119.00')
    wizard.back()
    wizard.back()
    wizard._profile_combo.setCurrentIndex(1)
    assert not wizard.transactions and wizard._details.rowCount() == 0
    wizard.close()


def test_invalid_headers_mappings_and_row_errors_block_progress(tmp_path, isolated_profiles):
    path = _six_csv(tmp_path)
    wizard = _wizard(tmp_path, isolated_profiles, path=path)
    original = path.read_text()
    path.write_text("ID;ID\na;b\n")
    wizard.next()
    assert wizard.currentId() == 0 and 'Zeile 1' in wizard._error.toPlainText()
    path.write_text(original)
    wizard.next()
    assert wizard.currentId() == 1
    wizard._bindings['currency'].setCurrentIndex(0)
    wizard.next()
    assert wizard.currentId() == 1 and 'Währung' in wizard._error.toPlainText()
    wizard._bindings['currency'].setCurrentIndex(wizard._bindings['currency'].findData('Umsatzkennung'))
    wizard.next()
    assert wizard.currentId() == 1 and 'mehrfach' in wizard._error.toPlainText()
    wizard._bindings['currency'].setCurrentIndex(wizard._bindings['currency'].findData('Waehrung'))
    path.write_text(original.replace('119,00', 'kein Betrag', 1))
    wizard.next()
    assert wizard.currentId() == 2
    assert 'Zeile 2' in wizard._error.toPlainText()
    assert not wizard.transactions
    assert not wizard.button(QWizard.WizardButton.NextButton).isEnabled()
    wizard.close()


def test_id_mapping_change_and_new_source_require_confirmation(tmp_path, isolated_profiles, monkeypatch):
    wizard = _wizard(tmp_path, isolated_profiles)
    _go_to_review(wizard)
    wizard.next()
    wizard._name.setText('Testbank')
    wizard._source.setCurrentText('Test Bank!')
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile is None
    assert '1 bis 128 Zeichen' in wizard._error.toPlainText()
    assert 'test_development' in wizard._error.toPlainText()
    wizard._source.setCurrentText('testbank')
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: warnings.append(a[2]) or QMessageBox.StandardButton.No)
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile is None and 'bisherige Kennung' in warnings[-1]
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: QMessageBox.StandardButton.Yes)
    wizard.button(QWizard.WizardButton.FinishButton).click()
    saved = isolated_profiles.load()[-1]
    wizard.close()
    edited = _wizard(tmp_path, isolated_profiles, profile=saved, edit_mapping=True, persist_profile=True)
    edited.next()
    assert edited.currentId() == 1
    edited._bindings['external_transaction_id'].setCurrentIndex(edited._bindings['external_transaction_id'].findData('Andere_ID'))
    edited.next()
    assert edited.transactions[0].external_transaction_id == 'NEU-1'
    edited.next()
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: warnings.append(a[2]) or QMessageBox.StandardButton.No)
    edited.button(QWizard.WizardButton.FinishButton).click()
    assert edited.profile is None and 'erneut buchbar' in warnings[-1]
    assert isolated_profiles.load()[-1] == saved
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: QMessageBox.StandardButton.Yes)
    edited.button(QWizard.WizardButton.FinishButton).click()
    assert edited.profile.import_source == saved.import_source
    edited.close()


def test_changed_file_and_failed_save_never_finish(tmp_path, isolated_profiles, monkeypatch):
    from simpleob.services.csv_import_profile_store import CsvImportProfileError
    wizard = _wizard(tmp_path, isolated_profiles, profile=qonto_compatibility_profile(), path=_csv(tmp_path), persist_profile=True)
    _go_to_review(wizard)
    wizard.next()
    original_save = isolated_profiles.save
    monkeypatch.setattr(isolated_profiles, 'save', lambda *a: (_ for _ in ()).throw(CsvImportProfileError('Nicht schreibbar')))
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile is None and 'Nicht schreibbar' in wizard._error.toPlainText()
    monkeypatch.setattr(isolated_profiles, 'save', original_save)
    wizard._csv_path.write_text(wizard._csv_path.read_text().replace('TEST-001', 'VERAENDERT'))
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile is None and not wizard.transactions
    assert 'seit der Vorschau geändert' in wizard._error.toPlainText()
    wizard.close()


def test_mapping_fields_remain_readable_at_usual_window_size(tmp_path, isolated_profiles):
    wizard = _wizard(tmp_path, isolated_profiles)
    wizard.resize(1000, 700)
    wizard.next()
    _APP.processEvents()
    combo = wizard._bindings['external_transaction_id']
    assert combo.width() >= 300
    assert combo.view().minimumWidth() >= 400
    assert 'Umsatzkennung' == combo.currentText()
    assert wizard.button(QWizard.WizardButton.NextButton).isVisible()
    assert wizard.button(QWizard.WizardButton.NextButton).geometry().bottom() < wizard.height()
    wizard.close()


def test_new_source_suggestion_preserves_manual_input_and_requires_explicit_reuse(tmp_path, isolated_profiles):
    wizard = _wizard(tmp_path, isolated_profiles)
    wizard._name.setText('Test_Development')
    assert wizard._source.currentText() == 'test_development'
    wizard._name.setText('123 Bank für Änne')
    assert wizard._source.currentText() == 'csv_123_bank_fur_anne'
    assert BankImportSource(wizard._source.currentText())
    wizard._name.setText('A' * 200)
    assert len(wizard._source.currentText()) == 128
    wizard._name.setText('Qonto CSV')
    assert wizard._source.currentText() == ''
    assert 'bereits vorhanden' in wizard._source.toolTip()
    wizard._name.setText('Andere Bank')
    assert wizard._source.currentText() == 'andere_bank'
    editor = wizard._source.lineEdit()
    editor.selectAll()
    QTest.keyClicks(editor, 'eigene.quelle')
    wizard._name.setText('Noch ein Name')
    assert wizard._source.currentText() == 'eigene.quelle'
    wizard._source.setCurrentIndex(wizard._source.findText('qonto_csv'))
    wizard._source.activated.emit(wizard._source.currentIndex())
    wizard._name.setText('Bewusst wiederverwendet')
    assert wizard._source.currentText() == 'qonto_csv'
    wizard.close()


def test_file_display_and_compact_summary_remain_accessible(tmp_path, isolated_profiles, monkeypatch):
    original = _six_csv(tmp_path)
    long_path = tmp_path / ('Sehr_langer_Dateiname_' * 6 + '.csv')
    original.rename(long_path)
    wizard = _wizard(tmp_path, isolated_profiles, path=long_path)
    wizard.resize(1000, 700)
    _APP.processEvents()
    assert wizard._file_name.text() == long_path.name
    assert wizard._file_name.toolTip() == str(long_path)
    assert wizard._file_name.width() > wizard.width() * 0.6
    replacement = tmp_path / 'Bank_Export.csv'
    replacement.write_bytes(long_path.read_bytes())
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **kw: (str(replacement), 'CSV'))
    wizard._choose_file()
    assert wizard._file_name.text() == replacement.name
    assert wizard._file_name.toolTip() == str(replacement)
    assert len(wizard._headers) == 8
    _go_to_review(wizard)
    wizard.next()
    _APP.processEvents()
    summary = wizard._settings_summary.text()
    for value in ('Bank_Export.csv', '6 Umsätze', 'Semikolon', 'UTF-8', '16.11.2026',
                  'Komma', 'Positive Werte', 'Umsatzkennung', 'Buchungstag', 'Betrag_EUR',
                  'Waehrung', 'Partner', 'Verwendungszweck', 'Bearbeitungsstand',
                  'gebucht → buchbar', 'vorgemerkt → nicht buchbar'):
        assert value in summary
    assert wizard._settings_summary.height() < 350
    wizard.back()
    wizard.back()
    for index in range(30):
        wizard._add_status(f'weiterer_bankstatus_{index}', 'not_settled')
    wizard.next()
    wizard.next()
    wizard.resize(820, 540)
    _APP.processEvents()
    scroll = wizard.page(3).findChild(QScrollArea)
    assert scroll.verticalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.verticalScrollBar().maximum() > 0
    assert wizard._name.isEnabled() and wizard._source.isEnabled()
    assert wizard.button(QWizard.WizardButton.FinishButton).isVisible()
    assert wizard.button(QWizard.WizardButton.FinishButton).isEnabled()
    assert wizard.button(QWizard.WizardButton.FinishButton).geometry().bottom() < wizard.height()
    wizard.close()


def test_saved_profile_direct_import_never_saves_or_opens_review(tmp_path, isolated_profiles, monkeypatch):
    profile = qonto_compatibility_profile()
    isolated_profiles.save((profile,))
    before = isolated_profiles.path.read_bytes()
    path = _csv(tmp_path)
    path.write_text(path.read_text() + 'TEST-002;pending;17.11.2026;Partner;Vorgemerkt;50,00;EUR\n')
    monkeypatch.setattr(isolated_profiles, 'save', lambda *a: pytest.fail('Beim Wiederverwenden darf nicht gespeichert werden.'))
    posted = []
    dialog = _dialog(duplicate_lookup=lambda transaction: uuid4() if transaction.external_transaction_id == 'TEST-001' else None,
                     post_proposal=lambda *a, **kw: posted.append(a))
    results = []

    def finish_directly():
        wizard = QApplication.activeModalWidget()
        try:
            assert wizard._original is None
            wizard._profile_combo.setCurrentIndex(1)
            _APP.processEvents()
            assert wizard.button(QWizard.WizardButton.FinishButton).isVisible()
            assert not wizard.button(QWizard.WizardButton.NextButton).isVisible()
            assert wizard.currentId() == 0 and wizard.nextId() == -1
            assert wizard.button(QWizard.WizardButton.FinishButton).text() == 'Zum Bankimport'
            wizard.button(QWizard.WizardButton.FinishButton).click()
            assert wizard.profile == profile
            assert wizard.visitedIds() == [0]
            results.append(True)
        except Exception as exc:
            results.append(exc)
            wizard.reject()

    QTimer.singleShot(0, finish_directly)
    assert dialog.start_import_assistant(csv_path=path)
    assert results == [True]
    assert len(dialog.transactions) == 2
    assert not dialog._checkbox(0).isEnabled()  # Bereits importiert.
    assert not dialog._checkbox(1).isEnabled()  # Vorgemerkt.
    assert 'Bereits übernommen' in dialog._table.item(0, 7).text()
    assert posted == []
    assert isolated_profiles.path.read_bytes() == before
    dialog.close()


def test_checkbox_changes_only_current_import_and_never_saves(tmp_path, isolated_profiles, monkeypatch):
    profile = qonto_compatibility_profile()
    isolated_profiles.save((profile,))
    before = isolated_profiles.path.read_bytes()
    monkeypatch.setattr(isolated_profiles, 'save', lambda *a: pytest.fail('Temporäre Zuordnung darf nicht gespeichert werden.'))
    dialog = _dialog()
    results = []

    def adjust_temporarily():
        wizard = QApplication.activeModalWidget()
        try:
            wizard._edit_mapping.setChecked(True)
            _APP.processEvents()
            assert wizard.button(QWizard.WizardButton.NextButton).isVisible()
            wizard.next()
            assert wizard.currentId() == 1
            wizard._positive.setCurrentIndex(wizard._positive.findData('outflow'))
            wizard.next()
            assert wizard.currentId() == 2 and wizard.nextId() == -1
            assert wizard.transactions[0].amount == Decimal('119.00')
            wizard.button(QWizard.WizardButton.FinishButton).click()
            assert wizard.profile.import_source == profile.import_source
            assert wizard.visitedIds() == [0, 1, 2]
            results.append(True)
        except Exception as exc:
            results.append(exc)
            wizard.reject()

    QTimer.singleShot(0, adjust_temporarily)
    assert dialog.start_import_assistant(profile=profile, csv_path=_csv(tmp_path))
    assert results == [True]
    assert dialog.transactions[0].amount == Decimal('119.00')
    assert dialog._profile_combo.currentData() == profile
    assert isolated_profiles.path.read_bytes() == before
    assert isolated_profiles.load() == (profile,)
    dialog.close()


def test_saved_profile_error_offers_temporary_correction_without_partial_import(tmp_path, isolated_profiles, monkeypatch):
    profile = qonto_compatibility_profile()
    isolated_profiles.save((profile,))
    before = isolated_profiles.path.read_bytes()
    path = _csv(tmp_path)
    path.write_text(path.read_text().replace('Transaction ID', 'Umsatznummer'))
    monkeypatch.setattr(isolated_profiles, 'save', lambda *a: pytest.fail('Fehlerkorrektur darf kein Profil überschreiben.'))
    wizard = _wizard(tmp_path, isolated_profiles, profile=profile, path=path)
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.currentId() == 0
    assert wizard.profile is None and not wizard.transactions
    assert 'Fehlende Pflichtspalten' in wizard._error.toPlainText()
    assert 'nur für diesen Import' in wizard._error.toPlainText()
    wizard._edit_mapping.setChecked(True)
    wizard.next()
    assert wizard.currentId() == 1
    wizard._bindings['external_transaction_id'].setCurrentIndex(wizard._bindings['external_transaction_id'].findData('Umsatznummer'))
    wizard.next()
    assert len(wizard.transactions) == 1
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: warnings.append(a[2]) or QMessageBox.StandardButton.No)
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile is None and 'erneut buchbar' in warnings[-1]
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: QMessageBox.StandardButton.Yes)
    wizard.button(QWizard.WizardButton.FinishButton).click()
    assert wizard.profile.columns.external_transaction_id.column == 'Umsatznummer'
    assert wizard.profile.import_source == profile.import_source
    assert isolated_profiles.path.read_bytes() == before
    wizard.close()
