"""PySide6-Hauptfenster von SimpleOB."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.ui.date_input import parse_german_date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.core.context import ApplicationContext
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.ui_qt.account_editor_dialog import AccountEditorDialog
from openbilanz.ui_qt.booking_frame import BookingFrame
from openbilanz.ui_qt.e_bilanz_account_mapping_dialog import (
    EBilanzAccountMappingDialog,
)
from openbilanz.ui_qt.vat_booking_frame import VatBookingFrame

ZERO = Decimal("0.00")


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        workspace: FiscalYearWorkspace,
        accounts: tuple[Account, ...],
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
        chart_of_accounts: ChartOfAccountsTemplate,
        opening_balance_account_number: str,
        closing_accounts: ClosingAccounts,
        vat_accounts: VatAccounts,
    ) -> None:
        super().__init__()

        self._context = context
        self._workspace = workspace
        self._accounts = accounts
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement
        self._chart_of_accounts = chart_of_accounts
        self._opening_balance_account_number = (
            opening_balance_account_number
        )
        self._closing_accounts = closing_accounts
        self._vat_accounts = vat_accounts

        self.setWindowTitle(
            f"SimpleOB – {self._context.company.name}"
        )
        self.resize(1300, 800)
        self.setMinimumSize(1100, 700)

        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        title_label = QLabel("SimpleOB")
        title_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Buchhaltung und Jahresabschluss"
        )
        layout.addWidget(subtitle_label)

        company_label = QLabel(
            f"Unternehmen: {self._context.company.name}"
        )
        company_label.setStyleSheet(
            "font-weight: bold;"
        )
        layout.addWidget(company_label)

        fiscal_year_label = QLabel(
            "Geschäftsjahr: "
            f"{self._context.fiscal_year.display_name}"
        )
        layout.addWidget(fiscal_year_label)

        self._notebook = QTabWidget()
        layout.addWidget(self._notebook)

        self._accounts_tab = QWidget()
        self._journal_tab = QWidget()
        self._booking_tab = QWidget()
        self._fixed_assets_tab = QWidget()
        self._balance_sheet_tab = QWidget()
        self._income_statement_tab = QWidget()
        self._reports_tab = QWidget()
        self._closing_tab = QWidget()
        self._e_bilanz_tab = QWidget()

        self._notebook.addTab(
            self._accounts_tab,
            "Konten",
        )
        self._notebook.addTab(
            self._journal_tab,
            "Journal",
        )
        self._notebook.addTab(
            self._booking_tab,
            "Buchen",
        )
        self._notebook.addTab(
            self._fixed_assets_tab,
            "Anlagen",
        )
        self._notebook.addTab(
            self._balance_sheet_tab,
            "Bilanz",
        )
        self._notebook.addTab(
            self._income_statement_tab,
            "GuV",
        )
        self._notebook.addTab(
            self._reports_tab,
            "Auswertungen",
        )
        self._notebook.addTab(
            self._closing_tab,
            "Jahresabschluss",
        )
        self._notebook.addTab(
            self._e_bilanz_tab,
            "E-Bilanz",
        )

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()

        self.setCentralWidget(central_widget)

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        layout = QVBoxLayout(self._accounts_tab)

        accounts_label = QLabel("Kontenübersicht")
        accounts_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(accounts_label)

        button_layout = QHBoxLayout()

        self._new_account_button = QPushButton(
            "Neues Konto"
        )
        self._new_account_button.clicked.connect(
            self._open_new_account
        )
        self._new_account_button.setEnabled(
            self._workspace.is_open
        )

        button_layout.addWidget(
            self._new_account_button
        )

        self._edit_account_button = QPushButton(
            "Konto bearbeiten"
        )
        self._edit_account_button.clicked.connect(
            self._open_edit_account
        )
        self._edit_account_button.setEnabled(
            not self._workspace.is_closed
        )

        button_layout.addWidget(
            self._edit_account_button
        )

        self._e_bilanz_mapping_button = QPushButton(
            "E-Bilanz-Zuordnung"
        )
        self._e_bilanz_mapping_button.clicked.connect(
            self._open_e_bilanz_account_mapping
        )

        button_layout.addWidget(
            self._e_bilanz_mapping_button
        )

        button_layout.addStretch()

        layout.addLayout(button_layout)

        self._journal_status = QLabel(
            f"Journal: {len(self._workspace.journal)} Buchungen"
        )
        layout.addWidget(self._journal_status)

        self._account_table = QTableWidget()
        self._account_table.setColumnCount(6)
        self._account_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Soll",
                "Haben",
                "Saldo",
                "E-Bilanz",
            )
        )

        self._account_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._account_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._account_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._account_table.setAlternatingRowColors(True)

        header = self._account_table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._account_table)

        self._refresh_accounts()

    def _create_booking_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Buchen."""

        layout = QVBoxLayout(self._booking_tab)

        booking_label = QLabel("Neue Buchung")
        booking_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(booking_label)

        mode_layout = QHBoxLayout()

        mode_layout.addWidget(
            QLabel("Buchungsart")
        )

        self._booking_mode_box = QComboBox()
        self._booking_mode_box.addItems(
            (
                "Einfache Buchung",
                "Rechnung mit Umsatzsteuer",
            )
        )
        self._booking_mode_box.setCurrentText(
            "Einfache Buchung"
        )
        self._booking_mode_box.setMaximumWidth(280)

        mode_layout.addWidget(
            self._booking_mode_box
        )
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
            *self._vat_accounts.account_numbers,
        }

        bookable_accounts = tuple(
            account
            for account in self._accounts
            if (
                account.is_active
                and account.number
                not in technical_account_numbers
            )
        )

        self._booking_frame_container = QWidget()
        self._booking_frame_layout = QVBoxLayout(
            self._booking_frame_container
        )
        self._booking_frame_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self._booking_frame = BookingFrame(
            self._booking_frame_container,
            accounts=bookable_accounts,
            on_booking_created=self._post_booking,
        )

        self._vat_booking_frame = VatBookingFrame(
            self._booking_frame_container,
            accounts=bookable_accounts,
            vat_accounts=self._vat_accounts,
            on_booking_created=self._post_booking,
        )

        self._booking_frame_layout.addWidget(
            self._booking_frame
        )
        self._booking_frame_layout.addWidget(
            self._vat_booking_frame
        )

        layout.addWidget(
            self._booking_frame_container
        )

        self._booking_mode_box.currentTextChanged.connect(
            self._update_booking_mode
        )

        enabled = self._workspace.is_open

        self._booking_frame.set_enabled(enabled)
        self._vat_booking_frame.set_enabled(enabled)
        self._booking_mode_box.setEnabled(enabled)

        self._update_booking_mode()

    def _update_booking_mode(
        self,
        *_args: object,
    ) -> None:
        """Schaltet zwischen einfacher und Umsatzsteuerbuchung um."""

        vat_mode = (
            self._booking_mode_box.currentText()
            == "Rechnung mit Umsatzsteuer"
        )

        self._booking_frame.setVisible(
            not vat_mode
        )
        self._vat_booking_frame.setVisible(
            vat_mode
        )

    def _post_booking(
        self,
        booking,
    ) -> None:
        """Verbucht und speichert eine Buchung."""

        if self._workspace.is_closed:
            return

        self._workspace.post_booking(
            booking
        )

        self._refresh_accounts()
        self._refresh_journal()

    def _create_journal_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Journal."""

        layout = QVBoxLayout(self._journal_tab)

        journal_label = QLabel("Journal")
        journal_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(journal_label)

        self._journal_table = QTableWidget()
        self._journal_table.setColumnCount(6)
        self._journal_table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "S/H",
                "Betrag",
            )
        )

        self._journal_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._journal_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._journal_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._journal_table.setAlternatingRowColors(True)

        header = self._journal_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._journal_table)

        self._journal_reversal_button = QPushButton(
            "Buchung stornieren"
        )
        self._journal_reversal_button.clicked.connect(
            self._reverse_selected_journal_booking
        )
        layout.addWidget(
            self._journal_reversal_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        self._refresh_journal()

    def _refresh_journal(self) -> None:
        """Aktualisiert die Journalanzeige."""

        self._journal_table.setRowCount(0)
        self._journal_booking_ids: dict[int, UUID] = {}

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        for booking in self._workspace.journal:
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

                if line.is_debit:
                    side = "Soll"
                else:
                    side = "Haben"

                row = self._journal_table.rowCount()
                self._journal_table.insertRow(row)

                self._journal_booking_ids[
                    row
                ] = booking.booking_id

                values = (
                    (
                        booking.booking_date.strftime(
                            "%d.%m.%Y"
                        )
                        if first_line
                        else ""
                    ),
                    (
                        booking.voucher_no or ""
                        if first_line
                        else ""
                    ),
                    (
                        booking.description or ""
                        if first_line
                        else ""
                    ),
                    account_display,
                    side,
                    self._format_amount(
                        line.amount
                    ),
                )

                for column, value in enumerate(values):
                    item = QTableWidgetItem(
                        str(value)
                    )

                    if column == 4:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter
                        )

                    if column == 5:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        )

                    self._journal_table.setItem(
                        row,
                        column,
                        item,
                    )

                first_line = False

    def _reverse_selected_journal_booking(
        self,
    ) -> None:
        """Storniert die im Journal ausgewählte reguläre Buchung."""

        selected_rows = (
            self._journal_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.warning(
                self,
                "Buchung stornieren",
                (
                    "Bitte wählen Sie zuerst eine "
                    "Buchung im Journal aus."
                ),
            )
            return

        row = selected_rows[0].row()

        booking_id = self._journal_booking_ids.get(
            row
        )

        if booking_id is None:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Die ausgewählte Buchung konnte "
                    "nicht ermittelt werden."
                ),
            )
            return

        original_booking = next(
            (
                booking
                for booking in self._workspace.journal
                if booking.booking_id == booking_id
            ),
            None,
        )

        if original_booking is None:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Die ausgewählte Buchung konnte "
                    "im Journal nicht gefunden werden."
                ),
            )
            return

        if (
            original_booking.booking_type
            is not BookingType.REGULAR
        ):
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Nur reguläre Buchungen können "
                    "über das Journal storniert werden."
                ),
            )
            return

        if self._workspace.is_closed:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Das Geschäftsjahr ist abgeschlossen. "
                    "Eine Stornobuchung ist nicht mehr möglich."
                ),
            )
            return

        default_date = date.today()

        if not self._context.fiscal_year.contains(
            default_date
        ):
            default_date = (
                self._context.fiscal_year.end_date
            )

        reversal_date_text, accepted = (
            QInputDialog.getText(
                self,
                "Buchung stornieren",
                (
                    "Bitte geben Sie das Stornodatum ein "
                    "(TT.MM.JJJJ):"
                ),
                text=default_date.strftime(
                    "%d.%m.%Y"
                ),
            )
        )

        if not accepted:
            return

        try:
            reversal_date = parse_german_date(
                reversal_date_text
            )

            reversal_booking = (
                self._workspace
                .create_reversal_booking(
                    booking_id=booking_id,
                    reversal_date=reversal_date,
                )
            )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                str(exc),
            )
            return

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        preview_lines = []

        for line in reversal_booking.lines:
            account_name = account_names.get(
                line.account_number,
                "Unbekanntes Konto",
            )

            side = (
                "Soll"
                if line.side is EntrySide.DEBIT
                else "Haben"
            )

            preview_lines.append(
                (
                    f"{line.account_number} "
                    f"{account_name}\n"
                    f"    {side}: "
                    f"{self._format_amount(line.amount)}"
                )
            )

        preview = "\n\n".join(
            preview_lines
        )

        confirmation, accepted = (
            QInputDialog.getText(
                self,
                "Stornobuchung bestätigen",
                (
                    "Folgende Stornobuchung wird erzeugt:\n\n"
                    f"Datum: "
                    f"{reversal_booking.booking_date.strftime('%d.%m.%Y')}\n"
                    f"Buchungstext: "
                    f"{reversal_booking.description or ''}\n\n"
                    f"{preview}\n\n"
                    "Die ursprüngliche Buchung bleibt "
                    "unverändert bestehen.\n\n"
                    "Zum endgültigen Buchen geben Sie exakt "
                    "DURCHFÜHREN ein:"
                ),
            )
        )

        if not accepted:
            return

        if confirmation != "DURCHFÜHREN":
            QMessageBox.information(
                self,
                "Buchung stornieren",
                (
                    "Die Stornobuchung wurde nicht "
                    "durchgeführt."
                ),
            )
            return

        try:
            self._workspace.post_booking(
                reversal_booking
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                str(exc),
            )
            return

        self._refresh_journal()
        self._refresh_accounts()

        QMessageBox.information(
            self,
            "Buchung storniert",
            (
                "Die Stornobuchung wurde erfolgreich "
                "gebucht.\n\n"
                "Die ursprüngliche Buchung bleibt "
                "im Journal erhalten."
            ),
        )

    def _open_new_account(self) -> None:
        """Öffnet den Dialog zum Anlegen eines Kontos."""

        if not self._workspace.is_open:
            return

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.add_account(
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

        QMessageBox.information(
            self,
            "Konto angelegt",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Bitte schließen Sie die Buchhaltung und "
                "öffnen Sie sie erneut, damit der geänderte "
                "Kontenrahmen vollständig wirksam wird."
            ),
        )

    def _open_e_bilanz_account_mapping(self) -> None:
        """Bearbeitet die E-Bilanz-Zuordnung des ausgewählten Kontos."""

        selected_rows = (
            self._account_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "E-Bilanz-Zuordnung",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return

        row = selected_rows[0].row()

        account_number_item = self._account_table.item(
            row,
            0,
        )

        if account_number_item is None:
            return

        account_number = account_number_item.text()

        account = next(
            (
                item
                for item in self._accounts
                if item.number == account_number
            ),
            None,
        )

        if account is None:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                "Das ausgewählte Konto wurde nicht gefunden.",
            )
            return

        try:
            choices = self._workspace.account_taxonomy_choices(
                account_number=account_number,
                chart_of_accounts=self._chart_of_accounts,
            )

            mappings = (
                self._workspace
                .load_account_taxonomy_concepts()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                str(exc),
            )
            return

        if not choices:
            QMessageBox.information(
                self,
                "E-Bilanz-Zuordnung",
                (
                    "Für die HGB-Zuordnung dieses Kontos "
                    "stehen keine feineren "
                    "E-Bilanz-Taxonomiepositionen zur Auswahl."
                ),
            )
            return

        current_concept_name = mappings.get(
            account_number
        )

        dialog = EBilanzAccountMappingDialog(
            self,
            account_number=account.number,
            account_name=account.name,
            choices=choices,
            current_concept_name=current_concept_name,
        )

        dialog.exec()

        if not dialog.saved:
            return

        try:
            self._workspace.save_account_taxonomy_concept(
                account_number=account_number,
                concept_name=dialog.result,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                str(exc),
            )
            return

        if dialog.result is None:
            message = (
                "Die E-Bilanz-Zuordnung wurde entfernt."
            )
        else:
            message = (
                "Die E-Bilanz-Zuordnung wurde gespeichert."
            )

        self._refresh_accounts()

        QMessageBox.information(
            self,
            "E-Bilanz-Zuordnung",
            message,
        )

    def _open_edit_account(self) -> None:
        """Öffnet den Dialog zum Bearbeiten des ausgewählten Kontos."""

        if self._workspace.is_closed:
            return

        selected_rows = (
            self._account_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return

        row = selected_rows[0].row()

        account_number_item = self._account_table.item(
            row,
            0,
        )

        if account_number_item is None:
            return

        account_number = account_number_item.text()

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
            *self._vat_accounts.account_numbers,
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

        account = next(
            (
                item
                for item in self._accounts
                if item.number == account_number
            ),
            None,
        )

        if account is None:
            QMessageBox.critical(
                self,
                "Konto bearbeiten",
                "Das ausgewählte Konto wurde nicht gefunden.",
            )
            return

        mapping_rule = next(
            (
                rule
                for rule
                in self._chart_of_accounts.account_mapping_rules
                if rule.account_number == account_number
            ),
            None,
        )

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
            account=account,
            mapping_rule=mapping_rule,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.update_account(
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

        self._accounts = tuple(
            dialog.result.account
            if item.number == account_number
            else item
            for item in self._accounts
        )
        self._refresh_accounts()

        QMessageBox.information(
            self,
            "Konto geändert",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Bitte schließen Sie die Buchhaltung und "
                "öffnen Sie sie erneut, damit der geänderte "
                "Kontenrahmen vollständig wirksam wird."
            ),
        )

    def _refresh_accounts(self) -> None:
        """Aktualisiert die Kontenübersicht."""

        account_taxonomy_concepts = (
            self._workspace.load_account_taxonomy_concepts()
        )

        self._account_table.setRowCount(
            len(self._accounts)
        )

        for row, account in enumerate(self._accounts):
            debit = ZERO
            credit = ZERO
            debit_balance = ZERO
            credit_balance = ZERO

            try:
                ledger_account = self._workspace.ledger.get_account(
                    account.number
                )
            except KeyError:
                pass
            else:
                debit = ledger_account.debit
                credit = ledger_account.credit
                debit_balance = ledger_account.debit_balance
                credit_balance = ledger_account.credit_balance

            balance = self._display_account_balance(
                account_type=account.account_type,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
            )

            e_bilanz_mapping = (
                "✓"
                if account.number in account_taxonomy_concepts
                else ""
            )

            values = (
                account.number,
                account.name,
                self._format_amount(debit),
                self._format_amount(credit),
                balance,
                e_bilanz_mapping,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column in (2, 3, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                elif column == 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self._account_table.setItem(
                    row,
                    column,
                    item,
                )

        self._account_table.resizeRowsToContents()

    @staticmethod
    def _format_amount(amount: object) -> str:
        """Formatiert einen Betrag mit zwei Nachkommastellen."""

        value = Decimal(str(amount))
        formatted = f"{value:,.2f}"

        return (
            formatted
            .replace(",", "\x00")
            .replace(".", ",")
            .replace("\x00", ".")
        )

    @classmethod
    def _display_account_balance(
        cls,
        *,
        account_type: AccountType,
        debit_balance: object,
        credit_balance: object,
    ) -> str:
        """Formatiert den fachlichen Kontosaldo."""

        if account_type in (
            AccountType.ASSET,
            AccountType.EXPENSE,
        ):
            if debit_balance > ZERO:
                return cls._format_amount(debit_balance)

            if credit_balance > ZERO:
                return "-" + cls._format_amount(
                    credit_balance
                )

        if account_type in (
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.REVENUE,
        ):
            if credit_balance > ZERO:
                return cls._format_amount(credit_balance)

            if debit_balance > ZERO:
                return "-" + cls._format_amount(
                    debit_balance
                )

        return cls._format_amount(ZERO)
