"""Mandanten- und jahresbezogene Personenkontenauswertungen."""

from datetime import date

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.core.context import ApplicationContext
from simpleob.date_input import GermanDateEdit
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.reporting.person_account_report import PersonAccountSummary
from simpleob.services.fiscal_year_workspace import FiscalYearWorkspace


class PersonAccountReportsWidget(QWidget):
    """Zeigt Saldenübersichten und Kontenblätter der Personenkonten."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        workspace: FiscalYearWorkspace,
        person_accounts: tuple[PersonAccount, ...],
        opening_balance_account_number: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._workspace = workspace
        self._person_accounts = person_accounts
        self._opening_balance_account_number = opening_balance_account_number
        self._accounts_by_number = {
            item.account.number: item for item in person_accounts
        }
        self._summary: PersonAccountSummary | None = None
        self._create_ui()
        self._refresh()

    def update_person_accounts(
        self,
        person_accounts: tuple[PersonAccount, ...],
        opening_balance_account_number: str,
    ) -> None:
        self._person_accounts = person_accounts
        self._opening_balance_account_number = opening_balance_account_number
        self._accounts_by_number = {
            item.account.number: item for item in person_accounts
        }
        self._refresh()

    def refresh(self) -> None:
        """Berechnet Übersicht und Kontenblatt aus dem aktuellen Journal neu."""

        self._refresh()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        company_name = getattr(getattr(self._context, "company", None), "name", "")
        year_heading = f"Geschäftsjahr {self._context.fiscal_year.display_name}"
        layout.addWidget(QLabel(f"{company_name} · {year_heading}" if company_name else year_heading))

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Von:"))
        self._start_date = GermanDateEdit(
            value=self._context.fiscal_year.start_date
        )
        controls.addWidget(self._start_date)
        controls.addWidget(QLabel("Bis / Stichtag:"))
        self._end_date = GermanDateEdit(
            value=self._context.fiscal_year.end_date
        )
        controls.addWidget(self._end_date)
        controls.addWidget(QLabel("Ansicht:"))
        self._role_filter = QComboBox()
        self._role_filter.addItems(("Alle Konten", "Debitoren", "Kreditoren"))
        controls.addWidget(self._role_filter)
        controls.addStretch()
        layout.addLayout(controls)
        self._start_date.textChanged.connect(self._refresh)
        self._end_date.textChanged.connect(self._refresh)
        self._role_filter.currentIndexChanged.connect(self._refresh)

        self._overview_table = QTableWidget(0, 9)
        self._overview_table.setHorizontalHeaderLabels(
            (
                "Geschäftspartner",
                "Konto",
                "Rolle",
                "Anfangssaldo",
                "Sollumsatz",
                "Habenumsatz",
                "Endsaldo Soll",
                "Endsaldo Haben",
                "Endsaldo Richtung",
            )
        )
        self._overview_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._overview_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._overview_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._overview_table.itemSelectionChanged.connect(
            self._refresh_statement
        )
        layout.addWidget(self._overview_table)

        self._totals_label = QLabel()
        layout.addWidget(self._totals_label)
        self._statement_heading = QLabel(
            "Personenkonto auswählen, um das Kontenblatt anzuzeigen."
        )
        self._statement_heading.setStyleSheet("font-weight: bold")
        layout.addWidget(self._statement_heading)
        self._statement_table = QTableWidget(0, 7)
        self._statement_table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Referenz",
                "Buchungstext",
                "Soll",
                "Haben",
                "Laufender Saldo",
                "Buchungs-ID",
            )
        )
        self._statement_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._statement_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self._statement_table)

    def _date_range(self) -> tuple[date, date]:
        start_date = self._start_date.date_value()
        end_date = self._end_date.date_value()
        fiscal_year = self._context.fiscal_year
        if (
            start_date < fiscal_year.start_date
            or end_date > fiscal_year.end_date
            or end_date < start_date
        ):
            raise ValueError(
                "Der Zeitraum muss innerhalb des Geschäftsjahres liegen "
                "und das Enddatum darf nicht vor dem Anfangsdatum liegen."
            )
        return start_date, end_date

    def _refresh(self, *_args: object) -> None:
        selected_account_number = self._selected_account_number()
        if not self._person_accounts:
            self._summary = None
            self._overview_table.setRowCount(0)
            self._statement_table.setRowCount(0)
            self._totals_label.setText("Für diesen Mandanten sind keine Personenkonten angelegt.")
            return
        try:
            start_date, end_date = self._date_range()
            summary = self._workspace.build_person_account_summary(
                person_accounts=self._person_accounts,
                start_date=start_date,
                end_date=end_date,
                opening_balance_account_number=self._opening_balance_account_number,
            )
        except (TypeError, ValueError) as exc:
            self._summary = None
            self._overview_table.setRowCount(0)
            self._statement_table.setRowCount(0)
            self._totals_label.setText(str(exc))
            return

        self._summary = summary
        selected_role = self._role_filter.currentText()
        rows = tuple(
            row
            for row in summary.rows
            if selected_role == "Alle Konten"
            or (selected_role == "Debitoren" and row.role is PersonAccountRole.DEBITOR)
            or (selected_role == "Kreditoren" and row.role is PersonAccountRole.KREDITOR)
        )
        selection_model = self._overview_table.selectionModel()
        selection_blocker = QSignalBlocker(selection_model)
        selection_model.clearSelection()
        self._overview_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            direction = (
                "Soll"
                if row.ending_balance > 0
                else "Haben"
                if row.ending_balance < 0
                else "ausgeglichen"
            )
            values = (
                row.partner_name,
                row.account_number,
                "Debitor" if row.role is PersonAccountRole.DEBITOR else "Kreditor",
                self._amount(row.opening_balance),
                self._amount(row.debit_turnover),
                self._amount(row.credit_turnover),
                self._amount(row.ending_debit_balance),
                self._amount(row.ending_credit_balance),
                direction,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1:
                    item.setData(Qt.ItemDataRole.UserRole, row.account_number)
                self._overview_table.setItem(index, column, item)
        if selected_account_number is not None:
            for index, row in enumerate(rows):
                if row.account_number == selected_account_number:
                    self._overview_table.selectRow(index)
                    break
        del selection_blocker
        self._overview_table.resizeColumnsToContents()
        self._totals_label.setText(
            "Summen für die angezeigte Rolle: "
            f"Anfangssaldo Soll {self._amount(sum((max(row.opening_balance, 0) for row in rows), start=0))} · "
            f"Anfangssaldo Haben {self._amount(sum((max(-row.opening_balance, 0) for row in rows), start=0))} · "
            f"Sollumsatz {self._amount(sum((row.debit_turnover for row in rows), start=0))} · "
            f"Habenumsatz {self._amount(sum((row.credit_turnover for row in rows), start=0))} · "
            f"Endsaldo Soll {self._amount(sum((row.ending_debit_balance for row in rows), start=0))} · "
            f"Endsaldo Haben {self._amount(sum((row.ending_credit_balance for row in rows), start=0))}"
        )
        self._refresh_statement()

    def _selected_account_number(self) -> str | None:
        selected_rows = self._overview_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        item = self._overview_table.item(selected_rows[0].row(), 1)
        return (
            item.data(Qt.ItemDataRole.UserRole)
            if item is not None
            else None
        )

    def _refresh_statement(self) -> None:
        selected_rows = self._overview_table.selectionModel().selectedRows()
        if not selected_rows:
            self._statement_heading.setText(
                "Personenkonto auswählen, um das Kontenblatt anzuzeigen."
            )
            self._statement_table.setRowCount(0)
            return
        row_number = selected_rows[0].row()
        account_item = self._overview_table.item(row_number, 1)
        account_number = (
            account_item.data(Qt.ItemDataRole.UserRole)
            if account_item is not None
            else None
        )
        person_account = self._accounts_by_number.get(account_number)
        if person_account is None:
            return
        try:
            start_date, end_date = self._date_range()
            report = self._workspace.build_person_account_statement(
                person_account=person_account,
                start_date=start_date,
                end_date=end_date,
            )
        except (TypeError, ValueError) as exc:
            self._statement_table.setRowCount(0)
            self._statement_heading.setText(str(exc))
            return
        role = "Debitor" if report.role is PersonAccountRole.DEBITOR else "Kreditor"
        self._statement_heading.setText(
            f"{getattr(getattr(self._context, 'company', None), 'name', '')} · "
            f"{self._context.fiscal_year.display_name} · "
            f"{report.account_number} · {role} · {report.partner_name} · "
            f"Anfangssaldo zum Zeitraum: {self._amount(report.opening_balance)} · "
            f"Saldovortrag aus Vorjahr: {self._amount(report.carried_forward_balance)} · "
            f"Endsaldo: {self._amount(report.ending_balance)}"
        )
        self._statement_table.setRowCount(len(report.lines))
        for index, line in enumerate(report.lines):
            values = (
                line.booking_date.strftime("%d.%m.%Y"),
                line.voucher_no,
                ("Saldovortrag · " if line.is_opening else "") + line.description,
                self._amount(line.debit),
                self._amount(line.credit),
                self._amount(line.running_balance),
                str(line.booking_id),
            )
            for column, value in enumerate(values):
                self._statement_table.setItem(
                    index, column, QTableWidgetItem(value)
                )
        self._statement_table.resizeColumnsToContents()

    @staticmethod
    def _amount(value) -> str:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
