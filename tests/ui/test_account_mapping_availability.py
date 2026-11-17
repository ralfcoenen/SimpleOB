from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidget

from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.account_table_helpers import AccountNumberTableWidgetItem
from simpleob.ui_qt.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def _window(*, account_number="1210", is_closed=False, booked=True):
    _app()
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    account = SimpleNamespace(
        number=account_number,
        name="Testkonto",
        account_type=None,
        is_active=True,
    )
    window._workspace = SimpleNamespace(
        is_closed=is_closed,
        load_account_taxonomy_concepts=lambda: {
            account_number: "concept.existing",
        },
        account_has_bookings=Mock(return_value=booked),
        save_account_with_taxonomy_mapping=Mock(),
    )
    window._account_table = QTableWidget(1, 1, window)
    window._account_table.setItem(
        0,
        0,
        AccountNumberTableWidgetItem(account_number),
    )
    window._account_table.selectRow(0)
    window._accounts = (account,)
    window._chart_of_accounts = SimpleNamespace(
        account_mapping_rules=(),
    )
    window._assets = object()
    window._liabilities = object()
    window._income_statement = object()
    window._opening_balance_account_number = (
        "9000" if account_number == "9000" else "9001"
    )
    window._closing_accounts = SimpleNamespace(
        income_summary_account="8990",
        profit_account="8991",
        loss_account="8992",
    )
    window._vat_accounts = SimpleNamespace(account_numbers=frozenset())
    window._activate_account_editing_mode = Mock()
    window._reload_chart_of_accounts = Mock(
        return_value=(window._chart_of_accounts, window._accounts)
    )
    window._refresh_accounts = Mock()
    return window


def test_combined_editor_keeps_mapping_and_cancel_writes_nothing(monkeypatch):
    window = _window(booked=True)
    received = {}

    class CancelledEditor:
        def __init__(self, *_args, **kwargs):
            received.update(kwargs)
            self.result = None

        def exec(self):
            return 0

    monkeypatch.setattr(
        main_window_module,
        "AccountEditorDialog",
        CancelledEditor,
    )

    MainWindow._open_edit_account(window)

    assert received["taxonomy_concept_name"] == "concept.existing"
    assert received["taxonomy_mapping_enabled"] is True
    assert received["account_type_locked"] is True
    assert received["protect_technical_fields"] is False
    window._workspace.save_account_with_taxonomy_mapping.assert_not_called()
    window.close()


def test_technical_account_opens_with_field_specific_protection(monkeypatch):
    window = _window(account_number="9000", booked=False)
    received = {}

    class CancelledEditor:
        def __init__(self, *_args, **kwargs):
            received.update(kwargs)
            self.result = None

        def exec(self):
            return 0

    monkeypatch.setattr(
        main_window_module,
        "AccountEditorDialog",
        CancelledEditor,
    )

    MainWindow._open_edit_account(window)

    assert received["protect_technical_fields"] is True
    assert received["account_type_locked"] is False
    window.close()


def test_existing_mapping_is_saved_with_account_update(monkeypatch):
    window = _window(booked=False)
    result = SimpleNamespace(
        account=window._accounts[0],
        mapping_rule=None,
        taxonomy_concept_name="concept.updated",
    )

    class AcceptedEditor:
        def __init__(self, *_args, **_kwargs):
            self.result = result

        def exec(self):
            return 1

    monkeypatch.setattr(
        main_window_module,
        "AccountEditorDialog",
        AcceptedEditor,
    )
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "information",
        lambda *_args: None,
    )

    MainWindow._open_edit_account(window)

    window._workspace.save_account_with_taxonomy_mapping.assert_called_once_with(
        account=result.account,
        mapping_rule=None,
        taxonomy_concept_name="concept.updated",
        is_new=False,
    )
    window._activate_account_editing_mode.assert_called_once()
    window.close()


def test_closed_year_does_not_open_editor_or_save(monkeypatch):
    window = _window(is_closed=True)
    editor = Mock()
    monkeypatch.setattr(
        main_window_module,
        "AccountEditorDialog",
        editor,
    )

    MainWindow._open_edit_account(window)

    editor.assert_not_called()
    window._workspace.save_account_with_taxonomy_mapping.assert_not_called()
    window.close()
