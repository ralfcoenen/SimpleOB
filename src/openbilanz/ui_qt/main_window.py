"""PySide6-Hauptfenster von SimpleOB."""

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMainWindow,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.core.context import ApplicationContext
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace


ZERO = Decimal("0.00")


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        workspace: FiscalYearWorkspace,
        accounts: tuple[Account, ...],
    ) -> None:
        super().__init__()

        self._context = context
        self._workspace = workspace
        self._accounts = accounts

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

        self.setCentralWidget(central_widget)

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        layout = QVBoxLayout(self._accounts_tab)

        accounts_label = QLabel("Kontenübersicht")
        accounts_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(accounts_label)

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
