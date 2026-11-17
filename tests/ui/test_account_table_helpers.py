from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.account_table_helpers import (
    AccountNumberTableWidgetItem,
    select_account_row,
    set_default_account_sort,
)
from simpleob.ui_qt.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_account_numbers_sort_numerically():
    _app()
    table = QTableWidget(3, 2)
    for row, (number, name) in enumerate(
        (("100", "Hundert"), ("20", "Zwanzig"), ("3", "Drei"))
    ):
        table.setItem(row, 0, AccountNumberTableWidgetItem(number))
        table.setItem(row, 1, QTableWidgetItem(name))

    set_default_account_sort(table)

    assert table.isSortingEnabled()
    assert [table.item(row, 0).text() for row in range(3)] == [
        "3",
        "20",
        "100",
    ]
    table.close()


def test_account_selection_uses_number_after_sorting():
    _app()
    table = QTableWidget(3, 2)
    for row, (number, name) in enumerate(
        (("10", "Zebra"), ("2", "Alpha"), ("30", "Beta"))
    ):
        table.setItem(row, 0, AccountNumberTableWidgetItem(number))
        table.setItem(row, 1, QTableWidgetItem(name))
    table.setSortingEnabled(True)
    table.sortItems(1)

    assert select_account_row(table, "10")
    selected_rows = table.selectionModel().selectedRows()
    assert len(selected_rows) == 1
    assert table.item(selected_rows[0].row(), 0).text() == "10"
    assert table.currentItem().text() == "10"
    table.close()


def test_new_mandant_account_is_selected_after_sorted_refresh(monkeypatch):
    _app()
    new_account = SimpleNamespace(number="2")
    result = SimpleNamespace(
        account=new_account,
        mapping_rule=None,
        taxonomy_concept_name="new.concept",
    )

    class AcceptedAccountEditor:
        def __init__(self, *_args, **_kwargs):
            self.result = result

        @staticmethod
        def exec():
            return 1

    monkeypatch.setattr(
        main_window_module,
        "AccountEditorDialog",
        AcceptedAccountEditor,
    )
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "information",
        lambda *_args: None,
    )
    table = QTableWidget(0, 1)
    accounts = tuple(SimpleNamespace(number=value) for value in ("10", "2", "30"))

    def refresh_accounts():
        table.setSortingEnabled(False)
        table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            table.setItem(row, 0, AccountNumberTableWidgetItem(account.number))
        set_default_account_sort(table)

    window = SimpleNamespace(
        _workspace=SimpleNamespace(
            is_open=True,
            save_account_with_taxonomy_mapping=Mock(),
            account_taxonomy_choices_for_position=Mock(return_value=()),
            validate_account_taxonomy_concept_for_position=Mock(),
        ),
        _assets=object(),
        _liabilities=object(),
        _income_statement=object(),
        _activate_account_editing_mode=Mock(),
        _reload_chart_of_accounts=Mock(return_value=(object(), accounts)),
        _refresh_accounts=refresh_accounts,
        _account_table=table,
    )

    MainWindow._open_new_account(window)

    assert [table.item(row, 0).text() for row in range(table.rowCount())] == [
        "2",
        "10",
        "30",
    ]
    selected_rows = table.selectionModel().selectedRows()
    assert len(selected_rows) == 1
    assert table.item(selected_rows[0].row(), 0).text() == "2"
    window._workspace.save_account_with_taxonomy_mapping.assert_called_once_with(
        account=new_account,
        mapping_rule=None,
        taxonomy_concept_name="new.concept",
        is_new=True,
    )
    table.close()
