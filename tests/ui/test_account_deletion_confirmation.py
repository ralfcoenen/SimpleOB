"""Regressionstests für die Bestätigung der Kontenlöschung."""

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMainWindow,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt import main_window as main_window_module
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
    for row, number in enumerate(("7000", "7001", "7002")):
        window._account_table.setItem(row, 0, QTableWidgetItem(number))
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
        for number in ("7000", "7001", "7002")
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
    window.close()
    app.processEvents()
