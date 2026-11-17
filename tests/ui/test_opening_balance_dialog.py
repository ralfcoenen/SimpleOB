from decimal import Decimal

from PySide6.QtWidgets import QApplication

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt.opening_balance_dialog import OpeningBalanceDialog

_APP = QApplication.instance() or QApplication([])


def _account(number: str, name: str, kind: AccountType) -> Account:
    return Account(
        template=TemplateAccount(number, name, kind),
    )


def test_dialog_has_separate_saldo_columns_and_records_selected_side() -> None:
    equity = _account("2970", "Gewinn-/Verlustvortrag", AccountType.EQUITY)
    bank = _account("1200", "Bank", AccountType.ASSET)
    dialog = OpeningBalanceDialog(
        accounts=(equity, bank),
        excluded_account_numbers={"9000"},
    )

    assert [
        dialog._item_table.horizontalHeaderItem(column).text()
        for column in range(dialog._item_table.columnCount())
    ] == ["Konto", "Bezeichnung", "Sollsaldo", "Habensaldo"]

    dialog._account_combo.setCurrentIndex(
        dialog._account_combo.findText(str(equity))
    )
    dialog._debit_entry.setText("4.000,00")
    dialog._add_item()

    assert dialog._items[0].account.number == "2970"
    assert dialog._items[0].side is EntrySide.DEBIT
    assert dialog._items[0].amount == Decimal("4000.00")
    assert dialog._item_table.item(0, 2).text() == "4.000,00"
    assert dialog._item_table.item(0, 3).text() == ""

    dialog._account_combo.setCurrentIndex(
        dialog._account_combo.findText(str(bank))
    )
    dialog._credit_entry.setText("4.000,00")
    dialog._add_item()

    assert dialog._items[1].side is EntrySide.CREDIT
    assert dialog._item_table.item(1, 2).text() == ""
    assert dialog._item_table.item(1, 3).text() == "4.000,00"
    assert dialog._debit_total_label.text() == "Soll: 4.000,00 €"
    assert dialog._credit_total_label.text() == "Haben: 4.000,00 €"
    assert dialog._accept_button.isEnabled()

    dialog._items.clear()
    dialog.close()


def test_dialog_excludes_opening_account_and_non_balance_accounts() -> None:
    valid = _account("2970", "Vortrag", AccountType.EQUITY)
    opening = _account("9000", "Saldenvortrag", AccountType.EQUITY)
    revenue = _account("8400", "Umsatz", AccountType.REVENUE)
    expense = _account("6000", "Aufwand", AccountType.EXPENSE)

    dialog = OpeningBalanceDialog(
        accounts=(valid, opening, revenue, expense),
        excluded_account_numbers={"9000"},
    )

    assert tuple(account.number for account in dialog._accounts) == ("2970",)
    dialog.close()
