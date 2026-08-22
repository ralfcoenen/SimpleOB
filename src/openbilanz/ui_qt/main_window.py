"""Hauptfenster der experimentellen PySide6-Oberfläche."""

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.application.workspace_factory import (
    WorkspaceContext,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.money import ZERO
from openbilanz.ui_qt.account_editor_dialog import (
    AccountEditorDialog,
)
from openbilanz.ui_qt.accounts_page import AccountsPage
from openbilanz.ui_qt.accounts_table_model import (
    AccountTableRow,
)
from openbilanz.ui_qt.balance_sheet_page import BalanceSheetPage
from openbilanz.ui_qt.booking_page import BookingPage
from openbilanz.ui_qt.income_statement_page import (
    IncomeStatementPage,
)
from openbilanz.ui_qt.journal_page import JournalPage
from openbilanz.ui_qt.journal_table_model import JournalTableRow


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(
        self,
        *,
        workspace_context: WorkspaceContext,
        reload_workspace_context: Callable[
            [],
            WorkspaceContext,
        ],
    ) -> None:
        super().__init__()

        self._workspace_context = workspace_context
        self._reload_workspace_context = (
            reload_workspace_context
        )
        self._return_to_start_requested = False

        self.setWindowTitle("OpenBilanz – PySide6")
        self.resize(1100, 700)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._back_button = QPushButton(
            "Zurück zur Buchhaltungsauswahl"
        )
        self._back_button.clicked.connect(
            self._return_to_start
        )

        layout.addWidget(
            self._back_button
        )

        self.setCentralWidget(central_widget)

        self._create_tabs()

    def _create_tabs(self) -> None:
        """Erzeugt die Hauptarbeitsbereiche."""

        self._accounts_page = AccountsPage(
            rows=self._build_account_rows()
        )

        self._accounts_page.new_account_requested.connect(
            self._open_new_account
        )
        self._accounts_page.edit_account_requested.connect(
            self._open_edit_account
        )

        self._accounts_page.set_editing_enabled(
            self._workspace_context.workspace.is_open
        )

        self._tabs.addTab(
            self._accounts_page,
            "Konten",
        )

        self._journal_page = JournalPage(
            rows=self._build_journal_rows()
        )

        self._tabs.addTab(
            self._journal_page,
            "Journal",
        )

        self._booking_page = BookingPage(
            accounts=self._bookable_accounts(),
            vat_accounts=self._workspace_context.vat_accounts,
            on_booking_created=self._post_booking,
            enabled=self._workspace_context.workspace.is_open,
        )

        self._tabs.addTab(
            self._booking_page,
            "Buchen",
        )

        self._balance_sheet_page = BalanceSheetPage()
        self._income_statement_page = IncomeStatementPage()

        self._tabs.addTab(
            QWidget(),
            "Anlagen",
        )

        self._tabs.addTab(
            self._balance_sheet_page,
            "Bilanz",
        )

        self._tabs.addTab(
            self._income_statement_page,
            "GuV",
        )

        self._refresh_financial_statements()

        for tab_name in (
            "Auswertungen",
            "Jahresabschluss",
            "E-Bilanz",
        ):
            self._tabs.addTab(
                QWidget(),
                tab_name,
            )

    def _open_new_account(self) -> None:
        workspace = self._workspace_context.workspace

        if workspace.is_closed:
            return

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        dialog = AccountEditorDialog(
            parent=self,
            assets=financial_context.assets,
            liabilities=financial_context.liabilities,
            income_statement=(
                financial_context.income_statement
            ),
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        try:
            workspace.add_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Konto kann nicht angelegt werden",
                str(exc),
            )
            return

        self._reload_after_account_change()

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        QMessageBox.information(
            self,
            "Konto angelegt",
            "Das Konto wurde gespeichert.",
        )

    def _open_edit_account(self) -> None:
        workspace = self._workspace_context.workspace

        if workspace.is_closed:
            return

        account = self._accounts_page.selected_account()

        if account is None:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return

        account_number = account.number

        technical_account_numbers = {
            (
                self._workspace_context
                .opening_balance_account_number
            ),
            (
                self._workspace_context
                .closing_accounts
                .income_summary_account
            ),
            (
                self._workspace_context
                .closing_accounts
                .profit_account
            ),
            (
                self._workspace_context
                .closing_accounts
                .loss_account
            ),
            *(
                self._workspace_context
                .vat_accounts
                .account_numbers
            ),
        }

        if account_number in technical_account_numbers:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                (
                    "Dieses Konto ist als technisches "
                    "Steuerungskonto konfiguriert und kann "
                    "hier nicht bearbeitet werden."
                ),
            )
            return

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        mapping_rule = next(
            (
                rule
                for rule
                in (
                    financial_context
                    .chart_of_accounts
                    .account_mapping_rules
                )
                if rule.account_number == account_number
            ),
            None,
        )

        dialog = AccountEditorDialog(
            parent=self,
            assets=financial_context.assets,
            liabilities=financial_context.liabilities,
            income_statement=(
                financial_context.income_statement
            ),
            account=account,
            mapping_rule=mapping_rule,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        try:
            workspace.update_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Konto kann nicht geändert werden",
                str(exc),
            )
            return

        self._reload_after_account_change()

        QMessageBox.information(
            self,
            "Konto geändert",
            "Das Konto wurde gespeichert.",
        )

    def _reload_after_account_change(self) -> None:
        """Lädt den Anwendungskontext nach Kontenänderungen neu."""

        self._workspace_context = (
            self._reload_workspace_context()
        )

        self._accounts_page.model.replace_rows(
            self._build_account_rows()
        )

        self._accounts_page.set_editing_enabled(
            self._workspace_context.workspace.is_open
        )

        self._refresh_financial_statements()

    def _build_account_rows(
        self,
    ) -> tuple[AccountTableRow, ...]:
        workspace = self._workspace_context.workspace

        accounts = (
            self._workspace_context
            .financial_statement_context
            .accounts
        )

        rows: list[AccountTableRow] = []

        for account in accounts:
            debit = ZERO
            credit = ZERO
            debit_balance = ZERO
            credit_balance = ZERO

            try:
                ledger_account = (
                    workspace.ledger.get_account(
                        account.number
                    )
                )
            except KeyError:
                pass
            else:
                debit = ledger_account.debit
                credit = ledger_account.credit
                debit_balance = (
                    ledger_account.debit_balance
                )
                credit_balance = (
                    ledger_account.credit_balance
                )

            balance = self._display_balance(
                account_type=account.account_type,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
            )

            rows.append(
                AccountTableRow(
                    account=account,
                    debit=debit,
                    credit=credit,
                    balance=f"{balance:.2f}",
                )
            )

        return tuple(rows)

    @staticmethod
    def _display_balance(
        *,
        account_type: AccountType,
        debit_balance,
        credit_balance,
    ):
        if account_type in (
            AccountType.ASSET,
            AccountType.EXPENSE,
        ):
            return debit_balance - credit_balance

        return credit_balance - debit_balance

    def _build_journal_rows(
        self,
    ) -> tuple[JournalTableRow, ...]:
        """Erzeugt die Darstellungszeilen des Journals."""

        workspace = self._workspace_context.workspace

        accounts = (
            self._workspace_context
            .financial_statement_context
            .accounts
        )

        account_names = {
            account.number: account.name
            for account in accounts
        }

        rows: list[JournalTableRow] = []

        for booking in workspace.journal:
            first_line = True

            for line in booking.lines:
                account_name = account_names.get(
                    line.account_number,
                    "Unbekanntes Konto",
                )

                account_display = (
                    f"{line.account_number} – "
                    f"{account_name}"
                )

                rows.append(
                    JournalTableRow(
                        booking_date=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                            if first_line
                            else ""
                        ),
                        voucher_no=(
                            booking.voucher_no or ""
                            if first_line
                            else ""
                        ),
                        description=(
                            booking.description or ""
                            if first_line
                            else ""
                        ),
                        account=account_display,
                        side=(
                            "Soll"
                            if line.is_debit
                            else "Haben"
                        ),
                        amount=line.amount,
                    )
                )

                first_line = False

        return tuple(rows)

    def _bookable_accounts(self):
        technical_account_numbers = {
            self._workspace_context.opening_balance_account_number,
            self._workspace_context.closing_accounts.income_summary_account,
            self._workspace_context.closing_accounts.profit_account,
            self._workspace_context.closing_accounts.loss_account,
            *self._workspace_context.vat_accounts.account_numbers,
        }

        return tuple(
            account
            for account in (
                self._workspace_context
                .financial_statement_context
                .accounts
            )
            if (
                account.is_active
                and account.number
                not in technical_account_numbers
            )
        )

    def _refresh_financial_statements(
        self,
    ) -> None:
        """Aktualisiert Bilanz und GuV."""

        workspace = self._workspace_context.workspace

        result = (
            self._workspace_context
            .financial_statement_service
            .build(
                ledger=workspace.ledger,
                pre_closing_ledger=(
                    workspace.pre_closing_ledger
                ),
                is_closed=workspace.is_closed,
                context=(
                    self._workspace_context
                    .financial_statement_context
                ),
            )
        )

        self._income_statement_page.update_income_statement(
            income_statement=result.income_statement,
            net_income=result.net_income,
        )

        if result.mapping_error is not None:
            self._balance_sheet_page.show_mapping_error(
                result.mapping_error
            )
            return

        if result.balance_sheet is None:
            return

        self._balance_sheet_page.update_balance_sheet(
            result.balance_sheet
        )

    def _post_booking(
        self,
        booking: Booking,
    ) -> None:
        """Verbucht eine Buchung und aktualisiert die Qt-Anzeige."""

        workspace = self._workspace_context.workspace

        if workspace.is_closed:
            return

        workspace.post_booking(booking)

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        self._accounts_page.model.replace_rows(
            self._build_account_rows()
        )

        self._refresh_financial_statements()

    def _return_to_start(self) -> None:
        """Schließt das Hauptfenster und kehrt zur Auswahl zurück."""

        self._return_to_start_requested = True
        self.close()

    @property
    def return_to_start_requested(self) -> bool:
        """Gibt an, ob zur Buchhaltungsauswahl zurückgekehrt werden soll."""

        return self._return_to_start_requested
