"""Hauptfenster der OpenBilanz-Anwendung."""

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.journal import Journal
from openbilanz.domain.money import ZERO
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.opening_balance_service import (
    OpeningBalanceService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.ui.balance_sheet_frame import BalanceSheetFrame
from openbilanz.ui.booking_frame import BookingFrame
from openbilanz.ui.income_statement_frame import (
    IncomeStatementFrame,
)
from openbilanz.ui.opening_balance_dialog import (
    OpeningBalanceDialog,
)


class MainWindow(tk.Tk):
    """Hauptfenster von OpenBilanz."""

    def __init__(self) -> None:
        super().__init__()

        self.title("OpenBilanz")
        self.geometry("1100x700")
        self.minsize(850, 550)

        self._journal = Journal()
        self._ledger = Ledger()

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number="9000",
        )
        self._posting_service = PostingService()
        
        self._closing_service = ClosingService()

        (
            self._assets,
            self._liabilities,
        ) = create_hgb_balance_sheet_structure()

        self._income_statement = (
            create_hgb_income_statement_structure()
        )

        self._chart_of_accounts = (
            self._load_standard_chart_of_accounts()
        )

        self._accounts = tuple(
            Account(template=template_account)
            for template_account
            in self._chart_of_accounts.accounts
        )

        self._financial_statement_builder = (
            FinancialStatementBuilder(
                AccountMapper(
                    self._chart_of_accounts
                )
            )
        )

        self._account_types = {
            account.account_number: account.account_type
            for account
            in self._chart_of_accounts.accounts
        }

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        container = ttk.Frame(
            self,
            padding=16,
        )
        container.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            container,
            text="OpenBilanz",
            font=("TkDefaultFont", 24, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text="Buchhaltung und Jahresabschluss",
        ).pack(
            anchor="w",
            pady=(4, 16),
        )

        ttk.Button(
            container,
            text="Eröffnungsbilanz erfassen",
            command=self._open_opening_balance,
        ).pack(
            anchor="w",
            pady=(0, 16),
        )

        self._notebook = ttk.Notebook(
            container
        )
        self._notebook.pack(
            fill="both",
            expand=True,
        )

        self._accounts_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._journal_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._booking_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._balance_sheet_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._income_statement_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._notebook.add(
            self._accounts_tab,
            text="Konten",
        )
        self._notebook.add(
            self._journal_tab,
            text="Journal",
        )
        self._notebook.add(
            self._booking_tab,
            text="Buchen",
        )
        self._notebook.add(
            self._balance_sheet_tab,
            text="Bilanz",
        )
        self._notebook.add(
            self._income_statement_tab,
            text="GuV",
        )

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()
        self._create_balance_sheet_tab()
        self._create_income_statement_tab()

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        ttk.Label(
            self._accounts_tab,
            text="Kontenübersicht",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        self._journal_status = ttk.Label(
            self._accounts_tab,
            text="Journal: noch keine Buchungen",
        )
        self._journal_status.pack(
            anchor="w",
            pady=(8, 12),
        )

        columns = (
            "account_number",
            "name",
            "debit",
            "credit",
            "balance",
        )

        self._account_table = ttk.Treeview(
            self._accounts_tab,
            columns=columns,
            show="headings",
            height=12,
        )

        self._account_table.heading(
            "account_number",
            text="Konto",
        )
        self._account_table.heading(
            "name",
            text="Bezeichnung",
        )
        self._account_table.heading(
            "debit",
            text="Soll",
        )
        self._account_table.heading(
            "credit",
            text="Haben",
        )
        self._account_table.heading(
            "balance",
            text="Saldo",
        )

        self._account_table.column(
            "account_number",
            width=90,
            anchor="w",
        )
        self._account_table.column(
            "name",
            width=330,
            anchor="w",
        )
        self._account_table.column(
            "debit",
            width=120,
            anchor="e",
        )
        self._account_table.column(
            "credit",
            width=120,
            anchor="e",
        )
        self._account_table.column(
            "balance",
            width=140,
            anchor="e",
        )

        self._account_table.pack(
            fill="both",
            expand=True,
        )

    def _create_journal_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Journal."""

        ttk.Label(
            self._journal_tab,
            text="Journal",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        columns = (
            "date",
            "description",
            "debit_account",
            "credit_account",
            "amount",
        )

        self._journal_table = ttk.Treeview(
            self._journal_tab,
            columns=columns,
            show="headings",
            height=12,
        )

        self._journal_table.heading(
            "date",
            text="Datum",
        )
        self._journal_table.heading(
            "description",
            text="Buchungstext",
        )
        self._journal_table.heading(
            "debit_account",
            text="Soll",
        )
        self._journal_table.heading(
            "credit_account",
            text="Haben",
        )
        self._journal_table.heading(
            "amount",
            text="Betrag",
        )

        self._journal_table.column(
            "date",
            width=100,
            anchor="w",
        )
        self._journal_table.column(
            "description",
            width=280,
            anchor="w",
        )
        self._journal_table.column(
            "debit_account",
            width=100,
            anchor="w",
        )
        self._journal_table.column(
            "credit_account",
            width=100,
            anchor="w",
        )
        self._journal_table.column(
            "amount",
            width=140,
            anchor="e",
        )

        self._journal_table.pack(
            fill="both",
            expand=True,
            pady=(12, 0),
        )

    def _create_booking_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Buchen."""

        ttk.Label(
            self._booking_tab,
            text="Neue Buchung",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 16),
        )

        booking_frame = BookingFrame(
            self._booking_tab,
            accounts=self._accounts,
            on_booking_created=self._post_booking,
        )
        booking_frame.pack(
            fill="x",
            expand=False,
        )

    def _create_balance_sheet_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich Bilanz."""

        ttk.Label(
            self._balance_sheet_tab,
            text="Bilanz nach § 266 HGB",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        self._balance_sheet_frame = (
            BalanceSheetFrame(
                self._balance_sheet_tab
            )
        )
        self._balance_sheet_frame.pack(
            fill="both",
            expand=True,
        )

    def _create_income_statement_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich GuV."""

        ttk.Label(
            self._income_statement_tab,
            text="Gewinn- und Verlustrechnung nach § 275 HGB",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        self._income_statement_frame = (
            IncomeStatementFrame(
                self._income_statement_tab
            )
        )
        self._income_statement_frame.pack(
            fill="both",
            expand=True,
        )

    def _post_booking(
        self,
        booking: Booking,
    ) -> None:
        """Verbucht eine aus der GUI übergebene Buchung."""

        self._posting_service.post_booking(
            booking=booking,
            ledger=self._ledger,
            journal=self._journal,
        )

        self._refresh_all()

    def _open_opening_balance(self) -> None:
        """Erfasst und verbucht die Eröffnungsbilanz."""

        dialog = OpeningBalanceDialog(
            self
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        bookings = (
            self._opening_balance_service
            .create_bookings(
                opening_balance=dialog.result,
                booking_date=date.today(),
            )
        )

        for booking in bookings:
            self._posting_service.post_booking(
                booking=booking,
                ledger=self._ledger,
                journal=self._journal,
            )

        self._refresh_all()

    def _refresh_all(self) -> None:
        """Aktualisiert alle sichtbaren Buchhaltungsdaten."""

        self._refresh_overview()
        self._refresh_journal()
        self._refresh_balance_sheet()

        self.update_idletasks()

    def _refresh_overview(self) -> None:
        """Aktualisiert die Kontenübersicht."""

        self._journal_status.config(
            text=(
                f"Journal: "
                f"{len(self._journal)} Buchungen"
            )
        )

        for item in self._account_table.get_children():
            self._account_table.delete(item)

        for account in self._accounts:
            debit = ZERO
            credit = ZERO
            debit_balance = ZERO
            credit_balance = ZERO

            try:
                ledger_account = self._ledger.get_account(
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

            self._account_table.insert(
                "",
                "end",
                values=(
                    account.number,
                    account.name,
                    self._format_amount(debit),
                    self._format_amount(credit),
                    balance,
                ),
            )

        try:
            opening_account = self._ledger.get_account(
                "9000"
            )
        except KeyError:
            return

        opening_balance = (
            opening_account.debit_balance
            if opening_account.debit_balance > ZERO
            else opening_account.credit_balance
        )

        self._account_table.insert(
            "",
            "end",
            values=(
                "9000",
                "Eröffnungsbilanzkonto",
                self._format_amount(
                    opening_account.debit
                ),
                self._format_amount(
                    opening_account.credit
                ),
                self._format_amount(
                    opening_balance
                ),
            ),
        )

    def _refresh_journal(self) -> None:
        """Aktualisiert die Journalanzeige."""

        for item in (
            self._journal_table.get_children()
        ):
            self._journal_table.delete(
                item
            )

        for booking in self._journal:
            for (
                debit_account,
                credit_account,
                amount,
            ) in self._posting_service._pair_lines(
                booking
            ):
                self._journal_table.insert(
                    "",
                    "end",
                    values=(
                        booking.booking_date.strftime(
                            "%d.%m.%Y"
                        ),
                        booking.description or "",
                        debit_account,
                        credit_account,
                        self._format_amount(
                            amount
                        ),
                    ),
                )

    def _refresh_balance_sheet(self) -> None:
        """Erzeugt und aktualisiert die laufende Bilanz."""

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        income_statement_account_types = (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )

        balance_sheet_balances = tuple(
            balance
            for balance in self._ledger.balances()
            if self._account_types.get(
                balance.account_number
            )
            in balance_sheet_account_types
        )

        income_statement_balances = tuple(
            balance
            for balance in self._ledger.balances()
            if self._account_types.get(
                balance.account_number
            )
            in income_statement_account_types
        )

        income_statement_amounts = (
            self._financial_statement_builder.build(
                balances=income_statement_balances,
                root_positions=(
                    self._income_statement,
                ),
            )
        )

        income_statement = IncomeStatement(
            income_statement=self._income_statement,
            amounts=income_statement_amounts,
        )

        net_income = (
            self._closing_service.calculate_net_income(
                income_statement=income_statement,
            )
        )
        
        self._income_statement_frame.update_income_statement(
            income_statement=income_statement,
            net_income=net_income,
        )

        closing_result = ClosingResult(
            net_income=net_income,
        )

        equity = next(
            position
            for position in self._liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )

        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )

        try:
            amounts = (
                self._financial_statement_builder.build(
                    balances=balance_sheet_balances,
                    root_positions=(
                        self._assets,
                        self._liabilities,
                    ),
                    closing_result=closing_result,
                    result_position=result_position,
                )
            )
        except ValueError as exc:
            message = str(exc)

            if (
                "no debit position defined for account" not in message
                and "no credit position defined for account" not in message
            ):
                raise

            self._balance_sheet_frame.show_mapping_error(
                self._format_mapping_error(message)
            )
            return

        balance_sheet = BalanceSheet(
            assets=self._assets,
            liabilities=self._liabilities,
            amounts=amounts,
        )

        self._balance_sheet_frame.update_balance_sheet(
            balance_sheet
        )


    def _load_standard_chart_of_accounts(
        self,
    ) -> ChartOfAccountsTemplate:
        """Lädt den OpenBilanz-Standardkontenrahmen."""

        provider = (
            HgbFinancialStatementPositionProvider(
                (
                    self._assets,
                    self._liabilities,
                    self._income_statement,
                ),
            )
        )

        csv_file = (
            Path(__file__).resolve().parent.parent
            / "resources"
            / "chart_of_accounts"
            / "openbilanz_standard.csv"
        )

        return CsvChartOfAccountsImporter(
            position_provider=provider,
        ).load(csv_file)

    @staticmethod
    def _format_amount(
        amount: object,
    ) -> str:
        """Formatiert einen Geldbetrag."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @staticmethod
    def _format_mapping_error(
        message: str,
    ) -> str:
        """Formatiert einen Mappingfehler für die GUI."""

        if "no credit position defined for account" in message:
            account_number = message.rsplit(" ", 1)[-1]

            return (
                f"Konto {account_number} weist einen Habensaldo auf. "
                "Für diesen Fall ist keine Bilanzzuordnung hinterlegt."
            )

        if "no debit position defined for account" in message:
            account_number = message.rsplit(" ", 1)[-1]

            return (
                f"Konto {account_number} weist einen Sollsaldo auf. "
                "Für diesen Fall ist keine Bilanzzuordnung hinterlegt."
            )

        return message

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
                return cls._format_amount(
                    debit_balance
                )

            if credit_balance > ZERO:
                return (
                    "-"
                    + cls._format_amount(
                        credit_balance
                    )
                )

        if account_type in (
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.REVENUE,
        ):
            if credit_balance > ZERO:
                return cls._format_amount(
                    credit_balance
                )

            if debit_balance > ZERO:
                return (
                    "-"
                    + cls._format_amount(
                        debit_balance
                    )
                )

        return cls._format_amount(ZERO)