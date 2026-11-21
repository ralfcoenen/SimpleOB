"""Regressionstests für die Bestätigung der Kontenlöschung."""

from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMainWindow,
    QMessageBox,
    QTableWidget,
)

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.account_table_helpers import (
    AccountNumberTableWidgetItem,
    set_default_account_sort,
)
from simpleob.ui_qt.main_window import MainWindow


def test_cancel_is_default_and_keeps_multi_selection_unchanged(monkeypatch):
    app = QApplication.instance() or QApplication([])

    class Workspace:
        def __init__(self):
            self.deleted = False
            self.is_closed = False

        def load_all_account_taxonomy_concepts(self):
            return {"6.9": {"7000": "sample.concept"}}

        def delete_accounts(self, *, account_numbers):
            self.deleted = True
            raise AssertionError("Abbrechen darf nicht löschen")

    class Button:
        def __init__(self, label):
            self.label = label

    class MessageBox:
        Icon = QMessageBox.Icon
        ButtonRole = QMessageBox.ButtonRole
        instance = None

        def __init__(self, _parent=None):
            self.buttons = []
            type(self).instance = self

        def setIcon(self, icon):
            self.icon = icon

        def setWindowTitle(self, title):
            self.title = title

        def setText(self, text):
            self.text = text

        def setInformativeText(self, text):
            self.informative_text = text

        def addButton(self, label, _role):
            button = Button(label)
            self.buttons.append(button)
            return button

        def setDefaultButton(self, button):
            self.default_button = button

        def setEscapeButton(self, button):
            self.escape_button = button

        def exec(self):
            return 0

        def clickedButton(self):
            return self.buttons[0]

    monkeypatch.setattr(main_window_module, "QMessageBox", MessageBox)
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._account_table = QTableWidget(3, 1, window)
    window._account_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    window._account_table.setSelectionMode(
        QAbstractItemView.SelectionMode.ExtendedSelection
    )
    numbers = ("100", "20", "3")
    for row, number in enumerate(numbers):
        window._account_table.setItem(
            row,
            0,
            AccountNumberTableWidgetItem(number),
        )
    set_default_account_sort(window._account_table)
    selection = window._account_table.selectionModel()
    for row in (0, 1):
        selection.select(
            window._account_table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
    window._accounts = tuple(
        Account(
            template=TemplateAccount(
                number, f"Konto {number}", AccountType.ASSET
            )
        )
        for number in numbers
    )
    window._chart_of_accounts = ChartOfAccountsTemplate(
        "Test", tuple(account.template for account in window._accounts)
    )
    window._workspace = Workspace()

    MainWindow._delete_selected_accounts(window)

    prompt = MessageBox.instance
    assert [button.label for button in prompt.buttons] == [
        "Abbrechen",
        "Konten löschen",
    ]
    assert prompt.default_button.label == "Abbrechen"
    assert prompt.escape_button.label == "Abbrechen"
    assert "2 ausgewählten Konten" in prompt.text
    assert "Taxonomie- und HGB-Zuordnungen" in prompt.informative_text
    assert not window._workspace.deleted
    assert {
        window._account_table.item(index.row(), 0).text()
        for index in window._account_table.selectionModel().selectedRows()
    } == {"3", "20"}
    window.close()
    app.processEvents()


def test_confirmed_multi_delete_uses_selected_accounts_after_sort(monkeypatch):
    app = QApplication.instance() or QApplication([])

    class Workspace:
        is_closed = False

        def __init__(self):
            self.deleted = None

        @staticmethod
        def load_all_account_taxonomy_concepts():
            return {}

        def delete_accounts(self, *, account_numbers):
            self.deleted = account_numbers
            return {}

    class Button:
        def __init__(self, label):
            self.label = label

    class ConfirmingMessageBox:
        Icon = QMessageBox.Icon
        ButtonRole = QMessageBox.ButtonRole

        def __init__(self, _parent=None):
            self.buttons = []

        def setIcon(self, _icon):
            pass

        def setWindowTitle(self, _title):
            pass

        def setText(self, _text):
            pass

        def setInformativeText(self, _text):
            pass

        def addButton(self, label, _role):
            button = Button(label)
            self.buttons.append(button)
            return button

        def setDefaultButton(self, _button):
            pass

        def setEscapeButton(self, _button):
            pass

        def exec(self):
            return 0

        def clickedButton(self):
            return self.buttons[-1]

    monkeypatch.setattr(main_window_module, "QMessageBox", ConfirmingMessageBox)
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._account_table = QTableWidget(3, 1, window)
    window._account_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    window._account_table.setSelectionMode(
        QAbstractItemView.SelectionMode.ExtendedSelection
    )
    numbers = ("100", "20", "3")
    for row, number in enumerate(numbers):
        window._account_table.setItem(
            row,
            0,
            AccountNumberTableWidgetItem(number),
        )
    set_default_account_sort(window._account_table)
    selection = window._account_table.selectionModel()
    for row in (0, 1):
        selection.select(
            window._account_table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )
    window._accounts = tuple(
        Account(
            template=TemplateAccount(
                number,
                f"Konto {number}",
                AccountType.ASSET,
            )
        )
        for number in numbers
    )
    window._chart_of_accounts = ChartOfAccountsTemplate(
        "Test",
        tuple(account.template for account in window._accounts),
    )
    window._workspace = Workspace()
    window._activate_account_editing_mode = lambda: None
    window._reload_chart_of_accounts = lambda: (
        window._chart_of_accounts,
        window._accounts,
    )
    window._refresh_accounts = lambda: None

    MainWindow._delete_selected_accounts(window)

    assert window._workspace.deleted == ("3", "20")
    window.close()
    app.processEvents()


def test_person_account_delete_requires_confirmation_and_refreshes_views(monkeypatch):
    app = QApplication.instance() or QApplication([])

    class MessageBox:
        StandardButton = QMessageBox.StandardButton
        answers = []

        @classmethod
        def question(cls, *_args):
            cls.answers.append(_args[2])
            return cls.StandardButton.Yes

        @staticmethod
        def information(*_args):
            raise AssertionError("Keine Information erwartet")

        @staticmethod
        def warning(*_args):
            raise AssertionError("Keine Warnung erwartet")

        @staticmethod
        def critical(*_args):
            raise AssertionError("Kein Fehler erwartet")

    class PersonAccountRepositorySpy:
        def __init__(self):
            self.deleted = None

        def delete_account(self, *, company_id, account_number):
            self.deleted = (company_id, account_number)
            return {}

    monkeypatch.setattr(main_window_module, "QMessageBox", MessageBox)
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._account_table = QTableWidget(2, 1, window)
    window._account_table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    window._account_table.setItem(
        0, 0, AccountNumberTableWidgetItem("10000")
    )
    window._account_table.setItem(
        1, 0, AccountNumberTableWidgetItem("9000")
    )
    window._account_table.selectRow(0)
    person_account = Account(
        template=TemplateAccount("10000", "Kunde", AccountType.ASSET),
        person_account_role=PersonAccountRole.DEBITOR,
    )
    other_account = Account(
        template=TemplateAccount("9000", "Eigenkapital", AccountType.EQUITY)
    )
    window._accounts = (person_account, other_account)
    window._workspace = SimpleNamespace(is_closed=False)
    company_id = uuid4()
    window._context = SimpleNamespace(
        company=SimpleNamespace(company_id=company_id)
    )
    repository = PersonAccountRepositorySpy()
    window._person_account_repository = repository
    refreshed = []
    window._activate_account_editing_mode = lambda: None
    window._reload_chart_of_accounts = lambda: (None, (other_account,))
    window._refresh_accounts = lambda: refreshed.append("accounts")
    window._refresh_person_account_reports = lambda: refreshed.append("reports")

    MainWindow._delete_selected_accounts(window)

    assert repository.deleted == (company_id, "10000")
    assert "Geschäftspartner" in MessageBox.answers[0]
    assert refreshed == ["accounts", "reports"]
    assert window._accounts == (other_account,)
    window.close()
    app.processEvents()
