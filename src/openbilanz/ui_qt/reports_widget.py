"""PySide6-Oberfläche für die Buchhaltungsauswertungen."""

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.core.context import ApplicationContext
from openbilanz.domain.account import Account
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.pdf_reporting_service import PdfReportingService
from openbilanz.date_input import parse_german_date


class ReportsWidget(QWidget):
    """Stellt die Auswertungen des Geschäftsjahres bereit."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        workspace: FiscalYearWorkspace,
        accounts: tuple[Account, ...],
        opening_balance_account_number: str,
        pdf_reporting_service: PdfReportingService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._context = context
        self._workspace = workspace
        self._accounts = accounts
        self._opening_balance_account_number = (
            opening_balance_account_number
        )
        self._pdf_reporting_service = pdf_reporting_service

        self._current_trial_balance_report = None
        self._current_account_activity_reports = ()
        self._current_account_activity_start_date: date | None = None
        self._current_account_activity_end_date: date | None = None
        self._current_journal_report = None

        self._account_names = {
            account.number: account.name
            for account in accounts
        }

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt den Arbeitsbereich Auswertungen."""

        layout = QVBoxLayout(self)

        notebook = QTabWidget()
        layout.addWidget(notebook)

        self._trial_balance_tab = QWidget()
        self._account_activity_tab = QWidget()
        self._journal_tab = QWidget()

        notebook.addTab(
            self._trial_balance_tab,
            "Summen- und Saldenliste",
        )
        notebook.addTab(
            self._account_activity_tab,
            "Kontenauswertung",
        )
        notebook.addTab(
            self._journal_tab,
            "Journal",
        )

        self._create_trial_balance_tab()
        self._create_account_activity_tab()
        self._create_journal_tab()

    def _create_trial_balance_tab(self) -> None:
        """Erzeugt die Summen- und Saldenliste."""

        layout = QVBoxLayout(self._trial_balance_tab)

        title = QLabel("Summen- und Saldenliste")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title)

        layout.addWidget(
            QLabel(
                "Auswertung der Kontenbewegungen "
                "vor Jahresabschlussbuchungen."
            )
        )

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Von:"))
        self._trial_balance_start_date = QLineEdit(
            self._context.fiscal_year.start_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._trial_balance_start_date.setMaximumWidth(110)
        filter_layout.addWidget(
            self._trial_balance_start_date
        )

        filter_layout.addWidget(QLabel("Bis:"))
        self._trial_balance_end_date = QLineEdit(
            self._context.fiscal_year.end_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._trial_balance_end_date.setMaximumWidth(110)
        filter_layout.addWidget(
            self._trial_balance_end_date
        )

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(
            self._refresh_trial_balance
        )
        filter_layout.addWidget(refresh_button)

        export_button = QPushButton("PDF exportieren")
        export_button.clicked.connect(
            self._export_trial_balance_pdf
        )
        filter_layout.addWidget(export_button)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self._trial_balance_table = QTableWidget()
        self._trial_balance_table.setColumnCount(8)
        self._trial_balance_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Anfang Soll",
                "Anfang Haben",
                "Soll-Umsatz",
                "Haben-Umsatz",
                "Endsaldo Soll",
                "Endsaldo Haben",
            )
        )
        self._trial_balance_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._trial_balance_table.setAlternatingRowColors(
            True
        )
        layout.addWidget(self._trial_balance_table)

        self._trial_balance_totals = QLabel()
        layout.addWidget(self._trial_balance_totals)

    def _refresh_trial_balance(self) -> None:
        """Aktualisiert die Summen- und Saldenliste."""

        try:
            start_date = parse_german_date(
                self._trial_balance_start_date.text()
            )
            end_date = parse_german_date(
                self._trial_balance_end_date.text()
            )

            report = self._workspace.build_trial_balance_report(
                start_date=start_date,
                end_date=end_date,
                opening_balance_account_number=(
                    self._opening_balance_account_number
                ),
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Summen- und Saldenliste",
                str(exc),
            )
            return

        self._current_trial_balance_report = report

        self._trial_balance_start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )
        self._trial_balance_end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )

        self._trial_balance_table.setRowCount(
            len(report.rows)
        )

        for row_index, row in enumerate(report.rows):
            values = (
                row.account_number,
                self._account_names.get(
                    row.account_number,
                    "Unbekanntes Konto",
                ),
                f"{row.opening_debit:.2f}",
                f"{row.opening_credit:.2f}",
                f"{row.debit_turnover:.2f}",
                f"{row.credit_turnover:.2f}",
                f"{row.closing_debit:.2f}",
                f"{row.closing_credit:.2f}",
            )

            for column, value in enumerate(values):
                self._trial_balance_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self._trial_balance_table.resizeColumnsToContents()

        self._trial_balance_totals.setText(
            "Summen: "
            f"Anfang Soll {report.opening_debit_total:.2f} · "
            f"Anfang Haben {report.opening_credit_total:.2f} · "
            f"Soll-Umsatz {report.debit_turnover_total:.2f} · "
            f"Haben-Umsatz {report.credit_turnover_total:.2f} · "
            f"Endsaldo Soll {report.closing_debit_total:.2f} · "
            f"Endsaldo Haben {report.closing_credit_total:.2f}"
        )

    def _create_account_activity_tab(self) -> None:
        """Erzeugt die Kontenauswertung."""

        layout = QVBoxLayout(self._account_activity_tab)

        title = QLabel("Kontenauswertung")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title)

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Von:"))
        self._account_activity_start_date = QLineEdit(
            self._context.fiscal_year.start_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._account_activity_start_date.setMaximumWidth(110)
        filter_layout.addWidget(
            self._account_activity_start_date
        )

        filter_layout.addWidget(QLabel("Bis:"))
        self._account_activity_end_date = QLineEdit(
            self._context.fiscal_year.end_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._account_activity_end_date.setMaximumWidth(110)
        filter_layout.addWidget(
            self._account_activity_end_date
        )

        filter_layout.addWidget(QLabel("Konto von:"))
        self._account_from = QLineEdit()
        self._account_from.setMaximumWidth(90)
        filter_layout.addWidget(self._account_from)

        filter_layout.addWidget(QLabel("Konto bis:"))
        self._account_to = QLineEdit()
        self._account_to.setMaximumWidth(90)
        filter_layout.addWidget(self._account_to)

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(
            self._refresh_account_activity
        )
        filter_layout.addWidget(refresh_button)

        export_button = QPushButton("PDF exportieren")
        export_button.clicked.connect(
            self._export_account_activity_pdf
        )
        filter_layout.addWidget(export_button)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self._account_activity_table = QTableWidget()
        self._account_activity_table.setColumnCount(8)
        self._account_activity_table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Beleg",
                "Konto",
                "Bezeichnung",
                "Buchungstext",
                "Soll",
                "Haben",
                "Saldo",
            )
        )
        self._account_activity_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._account_activity_table.setAlternatingRowColors(
            True
        )
        layout.addWidget(self._account_activity_table)

    def _refresh_account_activity(self) -> None:
        """Aktualisiert die gefilterte Kontenauswertung."""

        try:
            start_date = parse_german_date(
                self._account_activity_start_date.text()
            )
            end_date = parse_german_date(
                self._account_activity_end_date.text()
            )

            from_account = self._account_from.text().strip()
            to_account = self._account_to.text().strip()

            if not from_account:
                raise ValueError(
                    "Bitte geben Sie mindestens "
                    "'Konto von' ein."
                )

            if not to_account:
                to_account = from_account
                self._account_to.setText(to_account)

            if (
                not from_account.isdigit()
                or not to_account.isdigit()
            ):
                raise ValueError(
                    "Die Kontonummern müssen numerisch sein."
                )

            if int(to_account) < int(from_account):
                raise ValueError(
                    "'Konto bis' darf nicht kleiner "
                    "als 'Konto von' sein."
                )

            account_numbers = tuple(
                account.number
                for account in self._accounts
                if (
                    int(from_account)
                    <= int(account.number)
                    <= int(to_account)
                )
            )

            statements = tuple(
                self._workspace.build_account_activity_report(
                    account_number=account_number,
                    start_date=start_date,
                    end_date=end_date,
                )
                for account_number in account_numbers
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Kontenauswertung",
                str(exc),
            )
            return

        self._current_account_activity_reports = statements
        self._current_account_activity_start_date = start_date
        self._current_account_activity_end_date = end_date

        self._account_activity_start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )
        self._account_activity_end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )

        rows = []

        for statement in statements:
            account_name = self._account_names.get(
                statement.account_number,
                "Unbekanntes Konto",
            )

            for line in statement.lines:
                rows.append(
                    (
                        line.booking_date.strftime("%d.%m.%Y"),
                        line.voucher_no,
                        statement.account_number,
                        account_name,
                        line.description,
                        f"{line.debit:.2f}",
                        f"{line.credit:.2f}",
                        f"{line.running_balance:.2f}",
                    )
                )

        self._account_activity_table.setRowCount(
            len(rows)
        )

        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                self._account_activity_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self._account_activity_table.resizeColumnsToContents()

    def _create_journal_tab(self) -> None:
        """Erzeugt die Journalauswertung."""

        layout = QVBoxLayout(self._journal_tab)

        title = QLabel("Journal")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title)

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Von:"))
        self._journal_start_date = QLineEdit(
            self._context.fiscal_year.start_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._journal_start_date.setMaximumWidth(110)
        filter_layout.addWidget(self._journal_start_date)

        filter_layout.addWidget(QLabel("Bis:"))
        self._journal_end_date = QLineEdit(
            self._context.fiscal_year.end_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._journal_end_date.setMaximumWidth(110)
        filter_layout.addWidget(self._journal_end_date)

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(
            self._refresh_journal
        )
        filter_layout.addWidget(refresh_button)

        export_button = QPushButton("PDF exportieren")
        export_button.clicked.connect(
            self._export_journal_pdf
        )
        filter_layout.addWidget(export_button)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self._journal_table = QTableWidget()
        self._journal_table.setColumnCount(8)
        self._journal_table.setHorizontalHeaderLabels(
            (
                "Nr.",
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "Bezeichnung",
                "S/H",
                "Betrag",
            )
        )
        self._journal_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._journal_table.setAlternatingRowColors(True)
        layout.addWidget(self._journal_table)

    def _refresh_journal(self) -> None:
        """Aktualisiert die gefilterte Journalauswertung."""

        try:
            start_date = parse_german_date(
                self._journal_start_date.text()
            )
            end_date = parse_german_date(
                self._journal_end_date.text()
            )

            report = self._workspace.build_journal_report(
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Journal",
                str(exc),
            )
            return

        self._current_journal_report = report

        self._journal_start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )
        self._journal_end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )

        self._journal_table.setRowCount(
            len(report.lines)
        )

        for row_index, line in enumerate(report.lines):
            values = (
                line.booking_number,
                line.booking_date.strftime("%d.%m.%Y"),
                line.voucher_no,
                line.description,
                line.account_number,
                self._account_names.get(
                    line.account_number,
                    "Unbekanntes Konto",
                ),
                (
                    "S"
                    if line.side is EntrySide.DEBIT
                    else "H"
                ),
                f"{line.amount:.2f}",
            )

            for column, value in enumerate(values):
                self._journal_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self._journal_table.resizeColumnsToContents()

    def _select_pdf_target(
        self,
        *,
        title: str,
        initial_file: str,
    ) -> Path | None:
        """Wählt eine PDF-Zieldatei."""

        filename, _ = QFileDialog.getSaveFileName(
            self,
            title,
            initial_file,
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return None

        return Path(filename)

    def _export_trial_balance_pdf(self) -> None:
        """Exportiert die Summen- und Saldenliste."""

        report = self._current_trial_balance_report

        if report is None:
            QMessageBox.warning(
                self,
                "Summen- und Saldenliste",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
            )
            return

        target = self._select_pdf_target(
            title="Summen- und Saldenliste als PDF exportieren",
            initial_file="Summen-und-Saldenliste.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_trial_balance(
                    report=report,
                    account_names=self._account_names,
                    company_name=self._context.company.name,
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Summen- und Saldenliste konnte "
                "nicht exportiert werden",
                str(exc),
            )
            return

        self._show_export_success(
            "Summen- und Saldenliste",
            exported_path,
        )

    def _export_account_activity_pdf(self) -> None:
        """Exportiert die Kontenauswertung."""

        if (
            not self._current_account_activity_reports
            or self._current_account_activity_start_date is None
            or self._current_account_activity_end_date is None
        ):
            QMessageBox.warning(
                self,
                "Kontenauswertung",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
            )
            return

        target = self._select_pdf_target(
            title="Kontenauswertung als PDF exportieren",
            initial_file="Kontenauswertung.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_account_activity(
                    reports=self._current_account_activity_reports,
                    account_names=self._account_names,
                    company_name=self._context.company.name,
                    start_date=(
                        self._current_account_activity_start_date
                    ),
                    end_date=(
                        self._current_account_activity_end_date
                    ),
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Kontenauswertung konnte nicht exportiert werden",
                str(exc),
            )
            return

        self._show_export_success(
            "Kontenauswertung",
            exported_path,
        )

    def _export_journal_pdf(self) -> None:
        """Exportiert die Journalauswertung."""

        report = self._current_journal_report

        if report is None:
            QMessageBox.warning(
                self,
                "Journal",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
            )
            return

        target = self._select_pdf_target(
            title="Journal als PDF exportieren",
            initial_file="Journal.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_journal(
                    report=report,
                    account_names=self._account_names,
                    company_name=self._context.company.name,
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

        self._show_export_success(
            "Journal",
            exported_path,
        )

    def _show_export_success(
        self,
        title: str,
        exported_path: Path,
    ) -> None:
        """Meldet einen erfolgreichen PDF-Export."""

        QMessageBox.information(
            self,
            title,
            "PDF erfolgreich exportiert.\n\n"
            f"{exported_path}",
        )
