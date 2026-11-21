"""Regressionstests für die Aktivierung geänderter Kontenrahmen."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QWidget,
)

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_position import FinancialStatementPosition
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.template_account import TemplateAccount
from simpleob.ui_qt import main_window as main_window_module
from simpleob.ui_qt.booking_frame import BookingFrame
from simpleob.ui_qt.main_window import MainWindow

_APP = QApplication.instance() or QApplication([])


def _activation_window(monkeypatch):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._account_editing_mode = True
    window._context = object()
    window._assets = object()
    window._liabilities = object()
    window._income_statement = object()
    chart = SimpleNamespace(account_mapping_rules=())
    accounts = (SimpleNamespace(number="1210", is_active=True),)
    window._reload_chart_of_accounts = Mock(return_value=(chart, accounts))
    controls = SimpleNamespace(
        income_summary_account="9998",
        profit_account="9999",
        loss_account="9997",
        opening_balance_account="9000",
        depreciation_expense_account="4830",
    )
    vat_accounts = SimpleNamespace(account_numbers=frozenset())
    workspace = Mock()
    workspace.load_account_configuration.return_value = (
        controls,
        vat_accounts,
        object(),
    )
    window._workspace = workspace
    window._booking_frame = Mock()
    window._opening_balance_button = QPushButton()
    window._company_master_data_button = QAction(window)
    window._shareholders_button = QAction(window)
    window._account_configuration_button = QAction(window)
    window._export_company_button = QAction(window)
    window._elster_certificate_action = QAction(window)
    window._elster_data_supplier_action = QAction(window)
    window._reports_widget = Mock()
    window._company_master_data = SimpleNamespace(supports_e_bilanz=False)
    window._export_client_transfer = None
    window._account_table = Mock()
    window._notebook = QTabWidget()
    window._accounts_tab = QWidget()
    window._journal_tab = QWidget()
    window._e_bilanz_tab = QWidget()
    window._notebook.addTab(window._accounts_tab, "Konten")
    window._notebook.addTab(window._journal_tab, "Journal")
    window._notebook.addTab(window._e_bilanz_tab, "E-Bilanz")
    window._notebook.setCurrentWidget(window._accounts_tab)
    window._activate_chart_button = QPushButton()
    window._company_master_data_button = QAction(window)
    window._shareholders_button = QAction(window)
    window._account_configuration_button = QAction(window)
    window._export_company_button = QAction(window)
    window._elster_certificate_action = QAction(window)
    window._elster_data_supplier_action = QAction(window)
    window._return_to_start_button = QPushButton()
    window._update_editing_state = Mock()
    window._selected_account_number = Mock(return_value="1210")
    window._refresh_accounts = Mock()
    window._refresh_journal = Mock()
    window._refresh_balance_sheet = Mock()
    window._refresh_closing = Mock()
    window._refresh_e_bilanz_availability = Mock()

    financial_context_kwargs = {}

    def create_context(**kwargs):
        financial_context_kwargs.update(kwargs)
        return SimpleNamespace(
            statement_builder="builder",
            income_statement="income-position",
            account_types={"1210": "asset"},
            account_mapper="mapper",
            accounts=accounts,
        )

    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.create_financial_statement_context",
        create_context,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.ClosingAccounts",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.ClosingService",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    selected = Mock()
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.select_account_row",
        selected,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.QMessageBox.critical",
        Mock(),
    )
    return window, workspace, chart, accounts, selected, financial_context_kwargs


def test_activation_updates_context_and_unlocks_same_window(monkeypatch):
    (
        window,
        workspace,
        chart,
        accounts,
        selected,
        financial_context_kwargs,
    ) = _activation_window(monkeypatch)
    original_context = window._context

    window._activate_chart_changes()

    workspace.activate_chart_context.assert_called_once()
    activation = workspace.activate_chart_context.call_args.kwargs
    assert activation["accounts"] == accounts
    assert activation["account_mapper"] == "mapper"
    assert activation["income_summary_account_number"] == "9998"
    assert (
        financial_context_kwargs["account_roles"]
        is workspace.load_account_configuration.return_value[2]
    )
    assert window._chart_of_accounts is chart
    assert window._accounts == accounts
    assert window._context is original_context
    assert not window._account_editing_mode
    assert not window._activate_chart_button.isEnabled()
    assert window._refresh_accounts.called
    assert window._refresh_journal.called
    assert window._refresh_balance_sheet.called
    selected.assert_called_once_with(window._account_table, "1210")


def test_failed_activation_keeps_booking_locked_and_can_be_retried(monkeypatch):
    (
        window,
        workspace,
        _chart,
        _accounts,
        _selected,
        _financial_context_kwargs,
    ) = _activation_window(monkeypatch)
    workspace.load_account_configuration.side_effect = RuntimeError(
        "Konfiguration nicht verfügbar"
    )
    window._activate_chart_button.setEnabled(True)

    window._activate_chart_changes()

    assert window._account_editing_mode
    assert window._activate_chart_button.isEnabled()
    workspace.activate_chart_context.assert_not_called()


def test_general_booking_frame_refreshes_account_choices_after_activation():
    old_account = Account(
        TemplateAccount("1210", "Forderungen alt", AccountType.ASSET)
    )
    updated_account = Account(
        TemplateAccount("1210", "Forderungen neu", AccountType.ASSET)
    )
    other_account = Account(
        TemplateAccount("1200", "Bank", AccountType.ASSET)
    )
    simple = BookingFrame(
        accounts=(old_account,),
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=Mock(),
    )
    simple_row = simple._rows[0]
    simple_row.account_entry.setText("1210")
    simple.update_accounts(
        accounts=(updated_account, other_account),
        equity_contribution_account_numbers=frozenset(),
    )

    assert simple_row.name_item.text() == "Forderungen neu"
    assert "1200 – Bank" in simple_row.completer.model().stringList()


def test_account_configuration_updates_bank_role_for_next_balance_calculation(
    monkeypatch,
):
    bank_position = FinancialStatementPosition(
        "HGB.266.AKTIVA.B.IV", "Bankguthaben"
    )
    account = TemplateAccount("198765", "Zahlungskonto", AccountType.ASSET)
    chart = ChartOfAccountsTemplate(
        "Test",
        (account,),
        account_mapping_rules=(
            AccountMappingRule("198765", bank_position, None),
        ),
    )
    mapper = AccountMapper(chart)
    roles = AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset({"198765"}),
        general_rate_sales_accounts=frozenset(),
    )
    controls = SimpleNamespace(
        opening_balance_account="9000",
        depreciation_expense_account="4830",
    )
    vat_accounts = object()
    workspace = Mock()
    workspace.load_account_configuration.return_value = (
        controls,
        vat_accounts,
        AccountingAccountRoles(
            cash_accounts=frozenset(),
            bank_accounts=frozenset(),
            general_rate_sales_accounts=frozenset(),
        ),
    )

    class Dialog:
        result = (controls, vat_accounts, roles)

        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            pass

    class MessageBox:
        @staticmethod
        def information(*_args):
            pass

        @staticmethod
        def critical(*_args):
            raise AssertionError("Die Konfiguration muss gültig sein")

    monkeypatch.setattr(main_window_module, "AccountConfigurationDialog", Dialog)
    monkeypatch.setattr(main_window_module, "QMessageBox", MessageBox)
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._workspace = workspace
    window._accounts = (Account(account),)
    window._account_mapper = mapper
    window._opening_balance_account_number = "9000"
    window._depreciation_expense_account_number = "4830"
    window._invalidate_built_e_bilanz = Mock()
    window._refresh_balance_sheet = Mock()

    MainWindow._open_account_configuration(window)

    workspace.update_account_configuration.assert_called_once_with(
        control_accounts=controls,
        vat_accounts=vat_accounts,
        account_roles=roles,
    )
    window._refresh_balance_sheet.assert_called_once()
    window._invalidate_built_e_bilanz.assert_called_once()
    assert mapper.bank_account_numbers == frozenset({"198765"})
    position, amount = mapper.map_balance(AccountBalance("198765", credit=100))
    assert position.code == "HGB.266.PASSIVA.C.2"
    assert amount == 100
    window.close()
