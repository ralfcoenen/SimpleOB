"""Hauptfenster der experimentellen PySide6-Oberfläche."""

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
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
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.domain.money import ZERO
from openbilanz.services.pdf_reporting_service import (
    PdfReportingService,
)
from openbilanz.ui_qt.account_activity_report_page import (
    AccountActivityReportPage,
)
from openbilanz.ui_qt.account_configuration_dialog import (
    AccountConfigurationDialog,
)
from openbilanz.ui_qt.account_editor_dialog import (
    AccountEditorDialog,
)
from openbilanz.ui_qt.accounts_page import AccountsPage
from openbilanz.ui_qt.accounts_table_model import (
    AccountTableRow,
)
from openbilanz.ui_qt.balance_sheet_page import BalanceSheetPage
from openbilanz.ui_qt.booking_page import BookingPage
from openbilanz.ui_qt.closing_page import (
    ClosingPage,
)
from openbilanz.ui_qt.fixed_asset_acquisition_link_dialog import (
    AcquisitionBookingCandidate,
    FixedAssetAcquisitionLinkDialog,
)
from openbilanz.ui_qt.fixed_asset_disposal_dialog import (
    FixedAssetDisposalDialog,
)
from openbilanz.ui_qt.fixed_asset_loss_dialog import (
    FixedAssetLossDialog,
)
from openbilanz.ui_qt.fixed_asset_report_page import (
    FixedAssetReportPage,
)
from openbilanz.ui_qt.fixed_assets_page import (
    FixedAssetsPage,
)
from openbilanz.ui_qt.income_statement_page import (
    IncomeStatementPage,
)
from openbilanz.ui_qt.journal_page import JournalPage
from openbilanz.ui_qt.journal_report_page import (
    JournalReportPage,
)
from openbilanz.ui_qt.journal_table_model import JournalTableRow
from openbilanz.ui_qt.new_fixed_asset_dialog import (
    FixedAssetAccountOption,
    NewFixedAssetDialog,
)
from openbilanz.ui_qt.reports_page import ReportsPage
from openbilanz.ui_qt.trial_balance_report_page import (
    TrialBalanceReportPage,
)


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
        pdf_reporting_service: PdfReportingService,
    ) -> None:
        super().__init__()

        self._workspace_context = workspace_context
        self._current_financial_statement_result = None
        self._reload_workspace_context = (
            reload_workspace_context
        )
        self._pdf_reporting_service = (
            pdf_reporting_service
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

        self._accounts_page.account_configuration_requested.connect(
            self._open_account_configuration
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
            vat_configuration=(
                self._workspace_context.workspace.vat_configuration
            ),
            on_booking_created=self._post_booking,
            enabled=self._workspace_context.workspace.is_open,
        )

        self._fixed_asset_report_page = (
            FixedAssetReportPage(
                build_report=(
                    self._build_fixed_asset_report
                ),
                on_export_pdf=(
                    self._export_fixed_asset_report_pdf
                ),
            )
        )

        self._tabs.addTab(
            self._booking_page,
            "Buchen",
        )

        self._balance_sheet_page = BalanceSheetPage()
        self._income_statement_page = IncomeStatementPage()

        self._fixed_assets_page = FixedAssetsPage(
            on_add=self._open_new_fixed_asset,
            on_edit=self._open_edit_fixed_asset,
            on_delete=self._delete_fixed_asset,
            on_link_acquisition=(
                self._open_link_fixed_asset_acquisition
            ),
            on_loss=self._open_fixed_asset_loss,
            on_process_depreciations=(
                self._process_depreciations
            ),
            on_dispose=self._open_fixed_asset_disposal,
        )
        self._tabs.addTab(
            self._fixed_assets_page,
            "Anlagen",
        )

        self._refresh_fixed_assets()

        self._tabs.addTab(
            self._balance_sheet_page,
            "Bilanz",
        )

        self._tabs.addTab(
            self._income_statement_page,
            "GuV",
        )

        self._trial_balance_report_page = (
            TrialBalanceReportPage(
                fiscal_year_start=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .start_date
                ),
                fiscal_year_end=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .end_date
                ),
                account_names={
                    account.number: account.name
                    for account in (
                        self._workspace_context
                        .financial_statement_context
                        .accounts
                    )
                },
                build_report=(
                    self._build_trial_balance_report
                ),
                on_export_pdf=(
                    self._export_trial_balance_pdf
                ),
            )
        )

        account_names = {
            account.number: account.name
            for account in (
                self._workspace_context
                .financial_statement_context
                .accounts
            )
        }

        self._account_activity_report_page = (
            AccountActivityReportPage(
                fiscal_year_start=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .start_date
                ),
                fiscal_year_end=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .end_date
                ),
                account_names=account_names,
                build_report=(
                    self._build_account_activity_report
                ),
                on_export_pdf=(
                    self._export_account_activity_pdf
                ),
            )
        )

        self._journal_report_page = (
            JournalReportPage(
                fiscal_year_start=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .start_date
                ),
                fiscal_year_end=(
                    self._workspace_context
                    .workspace
                    .context
                    .fiscal_year
                    .end_date
                ),
                account_names=account_names,
                build_report=(
                    self._build_journal_report
                ),
                on_export_pdf=(
                    self._export_journal_pdf
                ),
            )
        )

        self._reports_page = ReportsPage(
            trial_balance_page=(
                self._trial_balance_report_page
            ),
            account_activity_page=(
                self._account_activity_report_page
            ),
            journal_report_page=(
                self._journal_report_page
            ),
            fixed_asset_report_page=(
                self._fixed_asset_report_page
            ),
        )

        self._tabs.addTab(
            self._reports_page,
            "Auswertungen",
        )

        self._trial_balance_report_page.refresh_report()

        self._journal_report_page.refresh_report()

        self._fixed_asset_report_page.refresh_report()

        self._refresh_financial_statements()

        self._closing_page = ClosingPage(
            on_validate=self._validate_closing,
            on_close=self._close_fiscal_year,
        )

        self._tabs.addTab(
            self._closing_page,
            "Jahresabschluss",
        )

        self._refresh_closing()

        self._tabs.addTab(
            QWidget(),
            "E-Bilanz",
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

    def _export_fixed_asset_report_pdf(
        self,
    ) -> None:
        """Exportiert den aktuellen Anlagenbericht."""

        report = (
            self._fixed_asset_report_page
            .current_report
        )

        if report is None:
            QMessageBox.warning(
                self,
                "Anlagenbericht",
                (
                    "Bitte aktualisieren Sie zuerst "
                    "die Auswertung."
                ),
            )
            return

        target = self._select_pdf_target(
            title="Anlagenbericht als PDF exportieren",
            initialfile="Anlagenbericht.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service
                .export_fixed_asset_report(
                    report=report,
                    company_name=(
                        self._workspace_context
                        .workspace
                        .context
                        .company
                        .name
                    ),
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Anlagenbericht konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Anlagenbericht",
            (
                "PDF erfolgreich exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _open_account_configuration(self) -> None:
        """Öffnet die mandantenbezogene Kontenkonfiguration."""

        accounts = (
            self._workspace_context
            .financial_statement_context
            .accounts
        )

        dialog = AccountConfigurationDialog(
            accounts=accounts,
            control_accounts=(
                self._workspace_context.control_accounts
            ),
            vat_accounts=(
                self._workspace_context.vat_accounts
            ),
            parent=self,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace_context.workspace.update_account_configuration(
                control_accounts=(
                    dialog.result.control_accounts
                ),
                vat_accounts=(
                    dialog.result.vat_accounts
                ),
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Technische Konten können nicht gespeichert werden",
                str(exc),
            )
            return

        self._reload_after_account_change()

        QMessageBox.information(
            self,
            "Technische Konten",
            "Die Kontenkonfiguration wurde gespeichert.",
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

        self._booking_page.set_vat_accounts(
            self._workspace_context.vat_accounts
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

    def _fixed_asset_account_options(
        self,
    ) -> tuple[FixedAssetAccountOption, ...]:
        """Liefert die Anlagekonten des Mandanten."""

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        mapping_rules = {
            rule.account_number: rule
            for rule in (
                financial_context
                .chart_of_accounts
                .account_mapping_rules
            )
        }

        options: list[
            FixedAssetAccountOption
        ] = []

        for account in financial_context.accounts:
            if not account.is_active:
                continue

            if account.account_type is not AccountType.ASSET:
                continue

            rule = mapping_rules.get(
                account.number
            )

            if (
                rule is None
                or rule.debit_position is None
            ):
                continue

            position_code = (
                rule.debit_position.code
            )

            if not position_code.startswith(
                "HGB.266.AKTIVA.A"
            ):
                continue

            options.append(
                FixedAssetAccountOption(
                    account_number=account.number,
                    account_name=account.name,
                    position_code=position_code,
                )
            )

        return tuple(
            sorted(
                options,
                key=lambda option: (
                    option.account_number
                ),
            )
        )

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

        self._current_financial_statement_result = result

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

        account_details = (
            self._build_balance_sheet_account_details(
                result
            )
        )

        self._balance_sheet_page.update_balance_sheet(
            result.balance_sheet,
            account_details=account_details,
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

        self._trial_balance_report_page.refresh_report()

        self._trial_balance_report_page.set_account_names(
            {
                account.number: account.name
                for account in (
                    self._workspace_context
                    .financial_statement_context
                    .accounts
                )
            }
        )

        self._journal_report_page.refresh_report()

    def _return_to_start(self) -> None:
        """Schließt das Hauptfenster und kehrt zur Auswahl zurück."""

        self._return_to_start_requested = True
        self.close()

    @property
    def return_to_start_requested(self) -> bool:
        """Gibt an, ob zur Buchhaltungsauswahl zurückgekehrt werden soll."""

        return self._return_to_start_requested

    def _refresh_fixed_assets(self) -> None:
        """Aktualisiert die Anlagegüter."""

        workspace = self._workspace_context.workspace

        try:
            assets = workspace.list_fixed_assets()
        except RuntimeError:
            return

        self._fixed_assets_page.set_assets(
            assets
        )

        self._fixed_assets_page.set_editing_enabled(
            workspace.is_open
        )

        if hasattr(
            self,
            "_fixed_asset_report_page",
        ):
            self._fixed_asset_report_page.refresh_report()

    def _open_edit_fixed_asset(self) -> None:
        """Öffnet ein Anlagegut zur Bearbeitung."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        fixed_asset = (
            self._fixed_assets_page.selected_asset()
        )

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut bearbeiten",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        try:
            acquisition_linked = (
                workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
            )
            return

        dialog = NewFixedAssetDialog(
            company_id=(
                workspace.context.company.company_id
            ),
            asset_accounts=(
                self._fixed_asset_account_options()
            ),
            fixed_asset=fixed_asset,
            acquisition_linked=acquisition_linked,
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        try:
            workspace.update_fixed_asset(
                dialog.result
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde geändert.",
        )

    def _delete_fixed_asset(self) -> None:
        """Löscht ein noch nicht buchungswirksames Anlagegut."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        fixed_asset = (
            self._fixed_assets_page.selected_asset()
        )

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut löschen",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Anlagegut löschen",
            (
                f"Soll das Anlagegut "
                f"„{fixed_asset.asset_code} – "
                f"{fixed_asset.description}“ "
                "wirklich gelöscht werden?\n\n"
                "Dieser Vorgang kann nicht rückgängig "
                "gemacht werden."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            workspace.delete_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht gelöscht werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde gelöscht.",
        )

    def _open_new_fixed_asset(self) -> None:
        """Öffnet den Dialog für ein neues Anlagegut."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        dialog = NewFixedAssetDialog(
            company_id=(
                workspace.context.company.company_id
            ),
            asset_accounts=(
                self._fixed_asset_account_options()
            ),
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        try:
            workspace.add_fixed_asset(
                dialog.result
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht angelegt werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde angelegt.",
        )

    def _open_link_fixed_asset_acquisition(
        self,
    ) -> None:
        """Ordnet eine vorhandene Buchung einem Anlagegut zu."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        fixed_asset = (
            self._fixed_assets_page.selected_asset()
        )

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anschaffungsbuchung zuordnen",
                "Bitte wählen Sie zuerst ein Anlagegut aus.",
            )
            return

        candidates: list[
            AcquisitionBookingCandidate
        ] = []

        for booking in workspace.journal.bookings:
            for position, line in enumerate(
                booking.lines
            ):
                if (
                    line.account_number
                    != fixed_asset.asset_account_number
                ):
                    continue

                if (
                    line.side
                    is not EntrySide.DEBIT
                ):
                    continue

                if (
                    line.amount
                    != fixed_asset.acquisition_cost
                ):
                    continue

                candidates.append(
                    AcquisitionBookingCandidate(
                        booking_id=booking.booking_id,
                        booking_line_position=position,
                        booking_date_text=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                        ),
                        voucher_no=(
                            booking.voucher_no or ""
                        ),
                        description=(
                            booking.description or ""
                        ),
                        account_number=(
                            line.account_number
                        ),
                        amount=line.amount,
                    )
                )

        if not candidates:
            QMessageBox.information(
                self,
                "Anschaffungsbuchung zuordnen",
                (
                    "Es wurde keine passende "
                    "Anschaffungsbuchung gefunden."
                ),
            )
            return

        dialog = FixedAssetAcquisitionLinkDialog(
            candidates=tuple(candidates),
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        candidate = dialog.selected_candidate

        if candidate is None:
            return

        try:
            workspace.link_fixed_asset_acquisition(
                fixed_asset_id=(
                    fixed_asset.fixed_asset_id
                ),
                booking_id=(
                    candidate.booking_id
                ),
                booking_line_position=(
                    candidate.booking_line_position
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                (
                    "Anschaffungsbuchung konnte "
                    "nicht zugeordnet werden"
                ),
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Anschaffungsbuchung",
            (
                "Die Anschaffungsbuchung wurde "
                "dem Anlagegut zugeordnet."
            ),
        )

        self._refresh_fixed_assets()

    def _open_fixed_asset_loss(
        self,
    ) -> None:
        """Führt einen bestätigten Totalverlust eines Anlageguts aus."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        fixed_asset = (
            self._fixed_assets_page.selected_asset()
        )

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Totalverlust",
                "Bitte wählen Sie zuerst ein Anlagegut aus.",
            )
            return

        if (
            fixed_asset.status
            is not FixedAssetStatus.ACTIVE
        ):
            QMessageBox.information(
                self,
                "Totalverlust",
                "Das ausgewählte Anlagegut ist bereits abgegangen.",
            )
            return

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        expense_accounts = tuple(
            (
                account.number,
                account.name,
            )
            for account in financial_context.accounts
            if (
                financial_context.account_types.get(
                    account.number
                )
                is AccountType.EXPENSE
            )
        )

        dialog = FixedAssetLossDialog(
            fixed_asset=fixed_asset,
            expense_accounts=expense_accounts,
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        loss_date = dialog.result.loss_date

        try:
            proposal = (
                workspace
                .pending_fixed_asset_loss_depreciation(
                    fixed_asset_id=(
                        fixed_asset.fixed_asset_id
                    ),
                    loss_date=loss_date,
                )
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Totalverlust kann nicht vorbereitet werden",
                str(exc),
            )
            return

        if proposal is not None:
            answer = QMessageBox.question(
                self,
                "Abschreibung vor Totalverlust",
                (
                    "Vor dem Totalverlust ist noch eine "
                    "Abschreibung zu buchen.\n\n"
                    f"Betrag: {proposal.amount:.2f} €\n"
                    "Datum: "
                    f"{proposal.depreciation_date:%d.%m.%Y}\n\n"
                    "Soll diese Abschreibung jetzt gebucht werden?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

            try:
                workspace.confirm_depreciation(
                    proposal
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Abschreibung konnte nicht gebucht werden",
                    str(exc),
                )
                return

        answer = QMessageBox.question(
            self,
            "Totalverlust bestätigen",
            (
                f"Anlagegut: {fixed_asset.asset_code}\n"
                f"{fixed_asset.description}\n\n"
                f"Verlustdatum: {loss_date:%d.%m.%Y}\n\n"
                "Das Anlagegut wird vollständig ausgebucht "
                "und anschließend als abgegangen markiert.\n\n"
                "Totalverlust wirklich buchen?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            workspace.confirm_fixed_asset_loss(
                fixed_asset_id=(
                    fixed_asset.fixed_asset_id
                ),
                loss_date=loss_date,
                loss_expense_account_number=(
                    dialog.result
                    .loss_expense_account_number
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Totalverlust konnte nicht gebucht werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        self._accounts_page.model.replace_rows(
            self._build_account_rows()
        )

        self._refresh_financial_statements()

        self._trial_balance_report_page.refresh_report()
        self._journal_report_page.refresh_report()

        QMessageBox.information(
            self,
            "Totalverlust",
            "Das Anlagegut wurde vollständig ausgebucht.",
        )

    def _open_fixed_asset_disposal(
        self,
    ) -> None:
        """Startet den Verkauf eines Anlageguts."""

        workspace = self._workspace_context.workspace

        if not workspace.is_open:
            return

        fixed_asset = (
            self._fixed_assets_page.selected_asset()
        )

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut verkaufen",
                "Bitte wählen Sie zuerst ein Anlagegut aus.",
            )
            return

        if (
            fixed_asset.status
            is not FixedAssetStatus.ACTIVE
        ):
            QMessageBox.information(
                self,
                "Anlagegut verkaufen",
                "Nur aktive Anlagegüter können verkauft werden.",
            )
            return

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        settlement_accounts = tuple(
            (
                account.number,
                account.name,
            )
            for account in financial_context.accounts
            if (
                account.is_active
                and account.account_type
                in (
                    AccountType.ASSET,
                    AccountType.LIABILITY,
                )
            )
        )

        revenue_accounts = tuple(
            (
                account.number,
                account.name,
            )
            for account in financial_context.accounts
            if (
                account.is_active
                and account.account_type
                is AccountType.REVENUE
            )
        )

        expense_accounts = tuple(
            (
                account.number,
                account.name,
            )
            for account in financial_context.accounts
            if (
                account.is_active
                and account.account_type
                is AccountType.EXPENSE
            )
        )

        dialog = FixedAssetDisposalDialog(
            parent=self,
            fixed_asset=fixed_asset,
            settlement_accounts=settlement_accounts,
            revenue_accounts=revenue_accounts,
            expense_accounts=expense_accounts,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        result = dialog.result

        try:
            pending_depreciation = (
                workspace
                .pending_fixed_asset_disposal_depreciation(
                    fixed_asset_id=(
                        fixed_asset.fixed_asset_id
                    ),
                    disposal_date=result.disposal_date,
                )
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht verkauft werden",
                str(exc),
            )
            return

        if pending_depreciation is not None:
            answer = QMessageBox.question(
                self,
                "Abschreibung vor Verkauf",
                (
                    "Vor dem Verkauf muss noch eine "
                    "Abschreibung gebucht werden.\n\n"
                    f"Betrag: "
                    f"{pending_depreciation.amount:.2f} EUR\n"
                    f"Datum: "
                    f"{pending_depreciation.depreciation_date:%d.%m.%Y}\n\n"
                    "Abschreibung jetzt buchen?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

            try:
                workspace.confirm_depreciation(
                    pending_depreciation
                )
            except (ValueError, RuntimeError) as exc:
                QMessageBox.critical(
                    self,
                    "Abschreibung fehlgeschlagen",
                    str(exc),
                )
                return

        answer = QMessageBox.question(
            self,
            "Anlagenverkauf bestätigen",
            (
                f"{fixed_asset.asset_code} – "
                f"{fixed_asset.description}\n\n"
                f"Verkaufsdatum: "
                f"{result.disposal_date:%d.%m.%Y}\n"
                f"Netto-Verkaufspreis: "
                f"{result.net_sale_amount:.2f} EUR\n"
                "Umsatzsteuer: 19 %\n\n"
                "Anlagegut jetzt verkaufen?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            workspace.confirm_fixed_asset_disposal(
                fixed_asset_id=(
                    fixed_asset.fixed_asset_id
                ),
                disposal_date=result.disposal_date,
                net_sale_amount=result.net_sale_amount,
                settlement_account_number=(
                    result.settlement_account_number
                ),
                revenue_account_number=(
                    result.revenue_account_number
                ),
                output_tax_account_number=(
                    self._workspace_context
                    .vat_accounts
                    .output_tax_19
                ),
                book_value_expense_account_number=(
                    result.book_value_expense_account_number
                ),
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Anlagenverkauf fehlgeschlagen",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        self._refresh_financial_statements()

        QMessageBox.information(
            self,
            "Anlagegut verkauft",
            (
                "Der Anlagenverkauf wurde gebucht "
                "und das Anlagegut als abgegangen markiert."
            ),
        )

    def _process_depreciations(self) -> None:
        """Prüft und bucht offene Abschreibungen."""

        workspace = self._workspace_context.workspace

        try:
            proposals = (
                workspace.build_depreciation_proposals()
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Abschreibungen konnten nicht vorbereitet werden",
                str(exc),
            )
            return

        if not proposals:
            QMessageBox.information(
                self,
                "Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind keine "
                    "offenen Abschreibungen vorhanden."
                ),
            )
            return

        try:
            fixed_assets = workspace.list_fixed_assets()
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Anlagegüter konnten nicht geladen werden",
                str(exc),
            )
            return

        fixed_assets_by_id = {
            asset.fixed_asset_id: asset
            for asset in fixed_assets
        }

        for proposal in proposals:
            fixed_asset = fixed_assets_by_id.get(
                proposal.fixed_asset_id
            )

            if fixed_asset is None:
                QMessageBox.critical(
                    self,
                    "Abschreibung konnte nicht zugeordnet werden",
                    (
                        "Das zur Abschreibung gehörende "
                        "Anlagegut wurde nicht gefunden."
                    ),
                )
                break

            answer = QMessageBox.question(
                self,
                "Abschreibung bestätigen",
                (
                    "Für folgendes Anlagegut wurde eine "
                    "lineare Abschreibung ermittelt:\n\n"
                    f"Anlagen-ID: {fixed_asset.asset_code}\n"
                    f"Bezeichnung: {fixed_asset.description}\n\n"
                    f"Betrag: {proposal.amount:.2f} €\n"
                    "Aufwandskonto: "
                    f"{proposal.expense_account_number}\n"
                    "Anlagenkonto: "
                    f"{proposal.asset_account_number}\n"
                    "Datum: "
                    f"{proposal.depreciation_date:%d.%m.%Y}\n\n"
                    "Soll diese Abschreibung gebucht werden?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                break

            try:
                workspace.confirm_depreciation(
                    proposal
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Abschreibung konnte nicht gebucht werden",
                    str(exc),
                )
                break

        # Gebuchte AfA verändert Anlagen, Journal,
        # Konten, GuV und Bilanz.
        self._refresh_fixed_assets()

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        self._accounts_page.model.replace_rows(
            self._build_account_rows()
        )

        self._refresh_financial_statements()

        self._trial_balance_report_page.refresh_report()
        self._journal_report_page.refresh_report()

    def _build_fixed_asset_report(self):
        """Erzeugt den Anlagenbericht."""

        return (
            self._workspace_context
            .workspace
            .build_fixed_asset_report()
        )

    def _build_trial_balance_report(
        self,
        start_date,
        end_date,
    ):
        workspace = self._workspace_context.workspace

        return workspace.build_trial_balance_report(
            start_date=start_date,
            end_date=end_date,
            opening_balance_account_number=(
                self._workspace_context
                .opening_balance_account_number
            ),
        )

    def _build_account_activity_report(
        self,
        account_number,
        start_date,
        end_date,
    ):
        workspace = self._workspace_context.workspace

        return workspace.build_account_activity_report(
            account_number=account_number,
            start_date=start_date,
            end_date=end_date,
        )

    def _build_journal_report(
        self,
        start_date,
        end_date,
    ):
        """Erzeugt die Journal-Auswertung über den Workspace."""

        workspace = self._workspace_context.workspace

        return workspace.build_journal_report(
            start_date=start_date,
            end_date=end_date,
        )

    def _account_names(
        self,
    ) -> dict[str, str]:
        """Liefert Kontonummern und Kontobezeichnungen."""

        return {
            account.number: account.name
            for account in (
                self._workspace_context
                .financial_statement_context
                .accounts
            )
        }


    def _select_pdf_target(
        self,
        *,
        title: str,
        initialfile: str,
    ) -> Path | None:
        """Wählt die Zieldatei für einen PDF-Bericht."""

        filename, _selected_filter = (
            QFileDialog.getSaveFileName(
                self,
                title,
                initialfile,
                "PDF-Dateien (*.pdf);;Alle Dateien (*)",
            )
        )

        if not filename:
            return None

        path = Path(filename)

        if path.suffix.lower() != ".pdf":
            path = path.with_suffix(".pdf")

        return path

    def _export_trial_balance_pdf(self) -> None:
        """Exportiert die aktuelle Summen- und Saldenliste."""

        report = (
            self._trial_balance_report_page
            .current_report
        )

        if report is None:
            QMessageBox.warning(
                self,
                "Summen- und Saldenliste",
                (
                    "Bitte aktualisieren Sie zuerst "
                    "die Auswertung."
                ),
            )
            return

        target = self._select_pdf_target(
            title=(
                "Summen- und Saldenliste "
                "als PDF exportieren"
            ),
            initialfile=(
                "Summen-und-Saldenliste.pdf"
            ),
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service
                .export_trial_balance(
                    report=report,
                    account_names=self._account_names(),
                    company_name=(
                        self._workspace_context
                        .workspace
                        .context
                        .company
                        .name
                    ),
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                (
                    "Summen- und Saldenliste "
                    "konnte nicht exportiert werden"
                ),
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Summen- und Saldenliste",
            (
                "PDF erfolgreich exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _export_account_activity_pdf(self) -> None:
        """Exportiert die aktuelle Kontenauswertung."""

        start_date = (
            self._account_activity_report_page
            .current_start_date
        )
        end_date = (
            self._account_activity_report_page
            .current_end_date
        )

        if (
            start_date is None
            or end_date is None
        ):
            QMessageBox.warning(
                self,
                "Kontenauswertung",
                (
                    "Bitte aktualisieren Sie zuerst "
                    "die Auswertung."
                ),
            )
            return

        target = self._select_pdf_target(
            title=(
                "Kontenauswertung als PDF exportieren"
            ),
            initialfile="Kontenauswertung.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service
                .export_account_activity(
                    reports=(
                        self._account_activity_report_page
                        .current_reports
                    ),
                    account_names=self._account_names(),
                    company_name=(
                        self._workspace_context
                        .workspace
                        .context
                        .company
                        .name
                    ),
                    start_date=start_date,
                    end_date=end_date,
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                (
                    "Kontenauswertung konnte "
                    "nicht exportiert werden"
                ),
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Kontenauswertung",
            (
                "PDF erfolgreich exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _export_journal_pdf(self) -> None:
        """Exportiert die aktuelle Journalauswertung."""

        report = (
            self._journal_report_page.current_report
        )

        if report is None:
            QMessageBox.warning(
                self,
                "Journal",
                (
                    "Bitte aktualisieren Sie zuerst "
                    "die Auswertung."
                ),
            )
            return

        target = self._select_pdf_target(
            title="Journal als PDF exportieren",
            initialfile="Journal.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service
                .export_journal(
                    report=report,
                    account_names=self._account_names(),
                    company_name=(
                        self._workspace_context
                        .workspace
                        .context
                        .company
                        .name
                    ),
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Journal konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Journal",
            (
                "PDF erfolgreich exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _validate_closing(self) -> None:
        """Prüft den Jahresabschluss."""

        result = self._current_financial_statement_result

        if result is None:
            return

        if result.balance_sheet is None:
            message = (
                result.mapping_error
                or (
                    "Die Bilanz konnte nicht vollständig "
                    "ermittelt werden."
                )
            )

            QMessageBox.warning(
                self,
                "Jahresabschluss kann nicht geprüft werden",
                message,
            )
            return

        workspace = self._workspace_context.workspace

        try:
            depreciation_proposals = (
                workspace.build_depreciation_proposals()
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Abschreibungen konnten nicht geprüft werden",
                str(exc),
            )
            return

        if depreciation_proposals:
            QMessageBox.warning(
                self,
                "Offene Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind noch "
                    "Abschreibungen zu bearbeiten.\n\n"
                    "Bitte führen Sie zuerst im Bereich "
                    '"Anlagen" die Aktion '
                    '"Abschreibungen prüfen/buchen" aus.'
                ),
            )
            return

        consistency = workspace.validate_closing(
            balance_sheet=result.balance_sheet,
            income_statement=result.income_statement,
            closing_result=result.closing_result,
            balances=result.closing_balances,
            mapper=(
                self._workspace_context
                .financial_statement_context
                .account_mapper
            ),
        )

        self._closing_page.update_consistency(
            consistency
        )

    def _close_fiscal_year(self) -> None:
        """Schließt das Geschäftsjahr persistent ab."""

        workspace = self._workspace_context.workspace

        if workspace.is_closed:
            return

        result = self._current_financial_statement_result

        if result is None:
            return

        answer = QMessageBox.question(
            self,
            "Geschäftsjahr abschließen",
            (
                "Das Geschäftsjahr wird nun endgültig "
                "abgeschlossen.\n\n"
                "Dabei werden die Erfolgskonten abgeschlossen "
                "und weitere Buchungen in diesem Geschäftsjahr "
                "gesperrt.\n\n"
                "Möchten Sie fortfahren?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            closing_result = workspace.close_fiscal_year(
                income_statement=result.income_statement,
                chart_of_accounts=(
                    self._workspace_context
                    .financial_statement_context
                    .chart_of_accounts
                ),
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Jahresabschluss fehlgeschlagen",
                str(exc),
            )
            return

        self._refresh_after_change()

        self._closing_page.update_net_income(
            closing_result.net_income
        )

        self._closing_page.mark_closed()

        QMessageBox.information(
            self,
            "Jahresabschluss",
            (
                "Das Geschäftsjahr wurde erfolgreich "
                "abgeschlossen."
            ),
        )

    def _refresh_after_change(self) -> None:
        """Aktualisiert die Oberfläche nach umfassenden Änderungen."""

        self._workspace_context = (
            self._reload_workspace_context()
        )

        workspace = self._workspace_context.workspace

        self._journal_page.model.replace_rows(
            self._build_journal_rows()
        )

        self._accounts_page.model.replace_rows(
            self._build_account_rows()
        )

        self._accounts_page.set_editing_enabled(
            workspace.is_open
        )

        self._booking_page.set_enabled(
            workspace.is_open
        )

        self._booking_page.set_vat_accounts(
            self._workspace_context.vat_accounts
        )

        self._fixed_assets_page.set_editing_enabled(
            workspace.is_open
        )

        self._refresh_fixed_assets()

        self._refresh_financial_statements()

        self._trial_balance_report_page.refresh_report()

        self._trial_balance_report_page.set_account_names(
            {
                account.number: account.name
                for account in (
                    self._workspace_context
                    .financial_statement_context
                    .accounts
                )
            }
        )

        self._journal_report_page.refresh_report()

        self._fixed_asset_report_page.refresh_report()

        self._refresh_closing()

    def _refresh_closing(self) -> None:
        """Aktualisiert den sichtbaren Abschlussstatus."""

        workspace = self._workspace_context.workspace

        self._closing_page.update_fiscal_year_status(
            workspace.managed_fiscal_year.status
        )

        result = self._current_financial_statement_result

        if result is None:
            return

        self._closing_page.update_net_income(
            result.closing_result.net_income
        )

    def _build_balance_sheet_account_details(
        self,
        result,
    ) -> dict[
        str,
        tuple[tuple[str, Decimal], ...],
    ]:
        """Erzeugt Kontendetails für die Bilanzdarstellung."""

        financial_context = (
            self._workspace_context
            .financial_statement_context
        )

        account_names = {
            account.number: account.name
            for account in financial_context.accounts
        }

        balance_sheet_account_types = {
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        }

        details: dict[
            str,
            list[tuple[str, Decimal]],
        ] = {}

        for balance in result.closing_balances:
            account_type = (
                financial_context.account_types.get(
                    balance.account_number
                )
            )

            if account_type not in balance_sheet_account_types:
                continue

            try:
                position, amount = (
                    financial_context
                    .account_mapper
                    .map_balance(balance)
                )
            except ValueError:
                continue

            account_name = account_names.get(
                balance.account_number,
                "Unbekanntes Konto",
            )

            label = (
                f"{balance.account_number} "
                f"{account_name}"
            )

            details.setdefault(
                position.code,
                [],
            ).append(
                (
                    label,
                    amount,
                )
            )

        return {
            position_code: tuple(rows)
            for position_code, rows
            in details.items()
        }
