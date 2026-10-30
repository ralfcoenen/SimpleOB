"""Tests für die Kontenrollenauswahl im Kontenkonfigurationsdialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTabWidget

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.accounting_control_accounts import AccountingControlAccounts
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.account_configuration_dialog import AccountConfigurationDialog

_APP = QApplication.instance() or QApplication([])


def _show_roles_tab(dialog: AccountConfigurationDialog) -> None:
    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentIndex(2)
    dialog.show()
    _APP.processEvents()


def _dialog() -> AccountConfigurationDialog:
    accounts = tuple(
        Account(
            TemplateAccount(
                account_number=number,
                name=name,
                account_type=AccountType.ASSET,
            )
        )
        for number, name in (
            ("1000", "Kasse Betrieb"),
            ("1001", "Weitere Kasse"),
            ("1100", "Kundenforderungen"),
            ("1400", "Lieferantenguthaben"),
            ("1600", "Lieferantenverbindlichkeiten"),
            ("1610", "Kundenguthaben"),
            ("1800", "Bankkonto mit einer besonders langen Bezeichnung"),
            ("1801", "Zweites Bankkonto"),
            ("4000", "Umsatzerlöse"),
            ("4001", "Weitere Umsatzerlöse"),
        )
    )
    return AccountConfigurationDialog(
        None,
        accounts=accounts,
        control_accounts=AccountingControlAccounts(
            opening_balance_account="1000",
            income_summary_account="1000",
            profit_account="1000",
            loss_account="1000",
            profit_loss_carryforward_account="1000",
            statutory_reserve_account="1000",
            other_revenue_reserves_account="1000",
            distribution_liability_account="1000",
            depreciation_expense_account="1000",
            fixed_asset_disposal_gain_account="1000",
            fixed_asset_disposal_loss_account="1000",
        ),
        vat_accounts=VatAccounts(
            input_tax_7="1000",
            input_tax_19="1000",
            output_tax_7="1000",
            output_tax_19="1000",
        ),
        account_roles=AccountingAccountRoles(
            cash_accounts=frozenset({"1000"}),
            bank_accounts=frozenset({"1800"}),
            general_rate_sales_accounts=frozenset({"4000"}),
            customer_receivables=frozenset({"1100"}),
            supplier_payables=frozenset({"1600"}),
            customer_credit_balances=frozenset({"1610"}),
            supplier_credit_balances=frozenset({"1400"}),
        ),
    )


def _account_item(dialog, account_number: str):
    for index in range(dialog._role_account_list.count()):
        item = dialog._role_account_list.item(index)
        if item.data(Qt.ItemDataRole.UserRole) == account_number:
            return item
    raise AssertionError(f"Konto {account_number} fehlt in der Liste")


def test_dialog_shows_all_seven_roles_and_full_account_labels():
    dialog = _dialog()
    _show_roles_tab(dialog)

    assert dialog._role_list.count() == 7
    assert dialog._role_list.item(0).text() == "Kasse"
    assert dialog._role_list.item(6).text() == "Lieferantenguthaben"
    item = _account_item(dialog, "1800")
    assert item.text() == "1800 – Bankkonto mit einer besonders langen Bezeichnung"
    assert dialog._role_account_list.width() > dialog._role_list.width()


def test_switching_roles_preserves_multiple_unsaved_assignments_until_save():
    dialog = _dialog()
    _account_item(dialog, "1001").setCheckState(Qt.CheckState.Checked)

    dialog._role_list.setCurrentRow(1)
    _account_item(dialog, "1801").setCheckState(Qt.CheckState.Checked)
    dialog._role_list.setCurrentRow(2)
    _account_item(dialog, "4001").setCheckState(Qt.CheckState.Checked)
    dialog._role_list.setCurrentRow(0)

    assert _account_item(dialog, "1001").checkState() == Qt.CheckState.Checked
    dialog._save()

    assert dialog.result[2].cash_accounts == frozenset({"1000", "1001"})
    assert dialog.result[2].bank_accounts == frozenset({"1800", "1801"})
    assert dialog.result[2].general_rate_sales_accounts == frozenset(
        {"4000", "4001"}
    )
    assert dialog.result is not None


def test_account_assigned_to_another_role_cannot_be_selected_twice():
    dialog = _dialog()
    dialog._role_list.setCurrentRow(1)

    item = _account_item(dialog, "1000")
    assert not item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert not item.flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert "Kasse" in item.toolTip()


def test_cancel_discards_unsaved_role_changes():
    dialog = _dialog()
    dialog._role_account_list.item(1).setCheckState(Qt.CheckState.Checked)

    dialog.reject()

    assert dialog.result is None
    assert dialog._account_roles.cash_accounts == frozenset({"1000"})


def test_roles_remain_usable_at_minimum_window_size():
    dialog = _dialog()
    dialog.resize(820, 680)
    _show_roles_tab(dialog)

    assert dialog.size().width() == 820
    assert dialog._role_list.isVisible()
    assert dialog._role_account_list.isVisible()
    assert dialog._role_account_list.width() >= 400
