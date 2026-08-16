"""Hauptfenster der OpenBilanz-Anwendung."""
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.error import URLError
from zipfile import BadZipFile

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_context import (
    FinancialStatementContext,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.journal import Journal
from openbilanz.domain.money import ZERO
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
)
from openbilanz.services.fiscal_year_workspace import (
    FiscalYearWorkspace,
)
from openbilanz.services.opening_balance_service import (
    OpeningBalanceService,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.ui.balance_sheet_frame import BalanceSheetFrame
from openbilanz.ui.booking_frame import BookingFrame
from openbilanz.ui.closing_frame import ClosingFrame
from openbilanz.ui.company_master_data_dialog import (
    CompanyMasterDataDialog,
)
from openbilanz.ui.income_statement_frame import (
    IncomeStatementFrame,
)
from openbilanz.ui.opening_balance_dialog import (
    OpeningBalanceDialog,
)


class MainWindow(tk.Tk):
    """Hauptfenster von OpenBilanz."""

    def __init__(
        self,
        *,
        workspace: FiscalYearWorkspace,
        financial_statement_context: FinancialStatementContext,
    ) -> None:
        super().__init__()

        self._workspace = workspace
        self._context = workspace.context
        self._financial_statement_context = (
            financial_statement_context
        )

        self.title("OpenBilanz")
        self.geometry("1100x700")
        self.minsize(850, 550)

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number="9000",
        )

        self._closing_service = ClosingService()

        self._assets = (
            financial_statement_context.assets
        )
        self._liabilities = (
            financial_statement_context.liabilities
        )
        self._income_statement = (
            financial_statement_context.income_statement
        )

        self._chart_of_accounts = (
            financial_statement_context.chart_of_accounts
        )
        self._accounts = (
            financial_statement_context.accounts
        )
        self._account_mapper = (
            financial_statement_context.account_mapper
        )
        self._financial_statement_builder = (
            financial_statement_context.statement_builder
        )
        self._account_types = (
            financial_statement_context.account_types
        )

        self._current_income_statement: (
            IncomeStatement | None
        ) = None

        self._current_closing_result: (
            ClosingResult | None
        ) = None

        self._current_balance_sheet: (
            BalanceSheet | None
        ) = None



        self._current_closing_balances = ()

        self._current_e_bilanz_preparation: (
            EBilanzPreparationResult | None
        ) = None

        self._current_e_bilanz_document: (
            EBilanzDocument | None
        ) = None

        self._create_ui()

        self._refresh_all()

    @property
    def _journal(self) -> Journal:
        """Liefert das Journal des aktuellen Workspace."""

        return self._workspace.journal

    @property
    def _ledger(self) -> Ledger:
        """Liefert das Hauptbuch des aktuellen Workspace."""

        return self._workspace.ledger

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

        context_frame = ttk.Frame(
            container,
        )
        context_frame.pack(
            fill="x",
            pady=(0, 16),
        )

        ttk.Label(
            context_frame,
            text=self._context.company.name,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            context_frame,
            text=(
                "Geschäftsjahr: "
                f"{self._context.fiscal_year.display_name}"
            ),
        ).pack(
            anchor="w",
            pady=(2, 0),
        )

        ttk.Button(
            context_frame,
            text="Unternehmensstammdaten",
            command=self._open_company_master_data,
        ).pack(
            anchor="w",
            pady=(8, 0),
        )

        self._opening_balance_button = ttk.Button(
            container,
            text="Eröffnungsbilanz erfassen",
            command=self._open_opening_balance,
        )
        self._opening_balance_button.pack(
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

        self._closing_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._e_bilanz_tab = ttk.Frame(
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

        self._notebook.add(
            self._closing_tab,
            text="Jahresabschluss",
        )

        self._notebook.add(
            self._e_bilanz_tab,
            text="E-Bilanz",
        )

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()
        self._create_balance_sheet_tab()
        self._create_income_statement_tab()
        self._create_closing_tab()
        self._create_e_bilanz_tab()

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
            "voucher",
            "description",
            "account",
            "side",
            "amount",
        )

        self._journal_table = ttk.Treeview(
            self._journal_tab,
            columns=columns,
            show="headings",
            height=14,
        )

        self._journal_table.heading(
            "date",
            text="Datum",
        )

        self._journal_table.heading(
            "voucher",
            text="Beleg",
        )

        self._journal_table.heading(
            "description",
            text="Buchungstext",
        )

        self._journal_table.heading(
            "account",
            text="Konto",
        )

        self._journal_table.heading(
            "side",
            text="S/H",
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
            "voucher",
            width=100,
            anchor="w",
        )

        self._journal_table.column(
            "description",
            width=230,
            anchor="w",
        )

        self._journal_table.column(
            "account",
            width=330,
            anchor="w",
        )

        self._journal_table.column(
            "side",
            width=60,
            anchor="center",
        )

        self._journal_table.column(
            "amount",
            width=130,
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

        self._booking_frame = BookingFrame(
            self._booking_tab,
            accounts=self._accounts,
            on_booking_created=self._post_booking,
        )

        self._booking_frame.pack(
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

    def _create_closing_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich Jahresabschluss."""

        self._closing_frame = ClosingFrame(
            self._closing_tab,
            on_validate=self._validate_closing,
            on_close=self._close_fiscal_year,
        )

        self._closing_frame.pack(
            fill="both",
            expand=True,
        )

    def _create_e_bilanz_tab(self) -> None:
        """Erzeugt den Arbeitsbereich E-Bilanz."""

        ttk.Label(
            self._e_bilanz_tab,
            text="E-Bilanz",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            self._e_bilanz_tab,
            text=(
                "Vorbereitung und Erzeugung der E-Bilanz "
                "für das aktuelle Geschäftsjahr."
            ),
        ).pack(
            anchor="w",
            pady=(4, 16),
        )

        self._taxonomy_status = ttk.Label(
            self._e_bilanz_tab,
            text="",
        )
        self._taxonomy_status.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._install_taxonomy_button = ttk.Button(
            self._e_bilanz_tab,
            text="Taxonomie installieren",
            command=self._install_required_taxonomy,
            state="disabled",
        )
        self._install_taxonomy_button.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._e_bilanz_status = ttk.Label(
            self._e_bilanz_tab,
            text="",
        )
        self._e_bilanz_status.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._prepare_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz vorbereiten",
            command=self._prepare_e_bilanz,
            state="disabled",
        )
        self._prepare_e_bilanz_button.pack(
            anchor="w",
        )
        self._build_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz erzeugen",
            command=self._build_e_bilanz,
            state="disabled",
        )
        self._build_e_bilanz_button.pack(
            anchor="w",
            pady=(8, 0),
        )
        self._validate_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz validieren",
            command=self._validate_e_bilanz,
            state="disabled",
        )
        self._validate_e_bilanz_button.pack(
            anchor="w",
            pady=(8, 0),
        )

    def _post_booking(
        self,
        booking: Booking,
    ) -> None:
        """Verbucht und speichert eine Buchung."""

        if self._workspace.is_closed:
            return

        self._workspace.post_booking(
            booking
        )

        self._refresh_all()

    def _open_opening_balance(self) -> None:
        """Erfasst, verbucht und speichert die Eröffnungsbilanz."""

        if self._workspace.is_closed:
            return

        dialog = OpeningBalanceDialog(
            self
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        bookings = (
            self._opening_balance_service.create_bookings(
                opening_balance=dialog.result,
                booking_date=self._context.fiscal_year.start_date,
            )
        )

        for booking in bookings:
            self._workspace.post_booking(
                booking
            )

        self._refresh_all()

    def _validate_closing(self) -> None:
        """Prüft den Jahresabschluss."""

        if (
            self._current_income_statement is None
            or self._current_closing_result is None
            or self._current_balance_sheet is None
        ):
            return

        result = self._workspace.validate_closing(
            balance_sheet=self._current_balance_sheet,
            income_statement=self._current_income_statement,
            closing_result=self._current_closing_result,
            balances=self._current_closing_balances,
            mapper=self._account_mapper,
        )

        self._closing_frame.update_consistency(
            result
        )

    def _close_fiscal_year(self) -> None:
        """Schließt das Geschäftsjahr persistent ab."""

        if self._workspace.is_closed:
            return

        if self._current_income_statement is None:
            return

        confirmed = messagebox.askyesno(
            "Geschäftsjahr abschließen",
            (
                "Das Geschäftsjahr wird endgültig abgeschlossen.\n\n"
                "Dabei werden die Erfolgskonten abgeschlossen und "
                "weitere Buchungen in diesem Geschäftsjahr gesperrt.\n\n"
                "Möchten Sie fortfahren?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            result = self._workspace.close_fiscal_year(
                income_statement=self._current_income_statement,
                chart_of_accounts=self._chart_of_accounts,
            )
        except ValueError as exc:
            messagebox.showerror(
                "Jahresabschluss fehlgeschlagen",
                str(exc),
                parent=self,
            )
            return

        self._refresh_all()

        self._closing_frame.update_net_income(
            result.net_income
        )

        self._closing_frame.mark_closed()

        messagebox.showinfo(
            "Jahresabschluss",
            "Das Geschäftsjahr wurde erfolgreich abgeschlossen.",
            parent=self,
        )

    def _refresh_all(self) -> None:
        """Aktualisiert alle sichtbaren Buchhaltungsdaten."""

        self._refresh_overview()
        self._refresh_journal()
        self._refresh_balance_sheet()
        self._refresh_closing()
        self._refresh_taxonomy_status()
        self._refresh_e_bilanz()
        self._update_editing_state()

        self.update_idletasks()

    def _refresh_taxonomy_status(self) -> None:
        """Aktualisiert den Taxonomiestatus des Geschäftsjahres."""

        status = self._workspace.taxonomy_status

        if status.complete:
            status_text = "installiert und vollständig"
        elif status.installed:
            status_text = "installiert, aber unvollständig"
        else:
            status_text = "nicht installiert"

        if status.usable:
            self._install_taxonomy_button.config(
                state="disabled"
            )
        else:
            self._install_taxonomy_button.config(
                state="normal"
            )

        self._taxonomy_status.config(
            text=(
                "Benötigte Taxonomie: "
                f"{status.required_version.value}\n"
                f"Status: {status_text}"
            ),
        )

    def _install_required_taxonomy(self) -> None:
        """Installiert die benötigte Taxonomie."""

        try:
            self._workspace.install_required_taxonomy()
        except (
            URLError,
            BadZipFile,
            ValueError,
            RuntimeError,
            OSError,
        ) as exc:
            messagebox.showerror(
                "Taxonomie konnte nicht installiert werden",
                str(exc),
                parent=self,
            )
            return

        self._refresh_taxonomy_status()
        self._refresh_e_bilanz()

        messagebox.showinfo(
            "Taxonomie",
            "Die benötigte Taxonomie wurde erfolgreich installiert.",
            parent=self,
        )

    def _refresh_e_bilanz(self) -> None:
        """Aktualisiert den Zustand des E-Bilanz-Arbeitsbereichs."""

        if not self._workspace.is_closed:
            self._e_bilanz_status.config(
                text=(
                    "Die E-Bilanz kann erst nach dem "
                    "Jahresabschluss vorbereitet werden."
                ),
            )
            self._prepare_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
            return

        self._prepare_e_bilanz_button.config(
            state="normal",
        )

        if self._current_e_bilanz_preparation is None:
            self._e_bilanz_status.config(
                text=(
                    "Das Geschäftsjahr ist abgeschlossen. "
                    "Die E-Bilanz kann vorbereitet werden."
                ),
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
            return

        preparation = self._current_e_bilanz_preparation

        taxonomy_status = self._workspace.taxonomy_status

        if taxonomy_status.usable:
            self._build_e_bilanz_button.config(
                state="normal",
            )
        else:
            self._build_e_bilanz_button.config(
                state="disabled",
            )


        if self._current_e_bilanz_document is None:
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
        else:
            self._validate_e_bilanz_button.config(
                state="normal",
            )

        status_text = (
            "Die E-Bilanz wurde vorbereitet.\n"
            f"Bilanzpositionen: "
            f"{len(preparation.balance_sheet_amounts)}\n"
            f"GuV-Positionen: "
            f"{len(preparation.income_statement_amounts)}"
        )

        if not taxonomy_status.usable:
            status_text += (
                "\n\n"
                "Die benötigte Taxonomie ist nicht "
                "vollständig installiert."
            )

        self._e_bilanz_status.config(
            text=status_text,
        )

    def _prepare_e_bilanz(self) -> None:
        """Bereitet die Abschlusswerte für die E-Bilanz auf."""

        if not self._workspace.is_closed:
            messagebox.showwarning(
                "E-Bilanz",
                "Das Geschäftsjahr ist noch nicht abgeschlossen.",
                parent=self,
            )
            return

        if self._current_income_statement is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Es steht keine GuV für die E-Bilanz-Vorbereitung zur Verfügung.",
                parent=self,
            )
            return



        try:
            preparation = self._workspace.prepare_e_bilanz(
                income_statement=self._current_income_statement,
            )
        except ValueError as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht vorbereitet werden",
                str(exc),
                parent=self,
            )
            return

        self._current_e_bilanz_preparation = preparation

        self._refresh_e_bilanz()

    def _build_e_bilanz(self) -> None:
        """Erzeugt die E-Bilanz aus den vorbereiteten Abschlusswerten."""

        if self._current_e_bilanz_preparation is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht vorbereitet.",
                parent=self,
            )
            return

        try:
            document = self._workspace.build_e_bilanz(
                preparation=self._current_e_bilanz_preparation,
            )
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht erzeugt werden",
                str(exc),
                parent=self,
            )
            return

        self._current_e_bilanz_document = document

        self._refresh_e_bilanz()

        messagebox.showinfo(
            "E-Bilanz",
            "Die E-Bilanz wurde erfolgreich erzeugt.",
            parent=self,
        )

    def _validate_e_bilanz(self) -> None:
        """Validiert die erzeugte E-Bilanz mit Arelle."""

        if self._current_e_bilanz_document is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht erzeugt.",
                parent=self,
            )
            return

        try:
            result = self._workspace.validate_e_bilanz(
                self._current_e_bilanz_document
            )
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht validiert werden",
                str(exc),
                parent=self,
            )
            return

        if result.is_valid:
            messagebox.showinfo(
                "E-Bilanz",
                "Die E-Bilanz wurde von Arelle "
                "erfolgreich validiert.",
                parent=self,
            )
            return

        errors = "\n".join(
            result.errors
        )

        messagebox.showerror(
            "E-Bilanz-Validierung fehlgeschlagen",
            (
                "Arelle hat Fehler in der "
                "E-Bilanz festgestellt.\n\n"
                f"{errors}"
            ),
            parent=self,
        )

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

        for item in self._journal_table.get_children():
            self._journal_table.delete(item)

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        account_names["9000"] = "Eröffnungsbilanzkonto"

        for booking in self._journal:
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

                self._journal_table.insert(
                    "",
                    "end",
                    values=(
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
                    ),
                )

                first_line = False

    def _refresh_balance_sheet(self) -> None:
        """Erzeugt und aktualisiert die laufende Bilanz."""

        self._current_balance_sheet = None

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
            and (
                balance.debit_balance > ZERO
                or balance.credit_balance > ZERO
            )
        )

        income_statement_ledger = (
            self._workspace.pre_closing_ledger
            if self._workspace.is_closed
            else self._ledger
        )

        income_statement_balances = tuple(
            balance
            for balance in income_statement_ledger.balances()
            if self._account_types.get(
                balance.account_number
            )
            in income_statement_account_types
            and (
                balance.debit_balance > ZERO
                or balance.credit_balance > ZERO
            )
        )

        self._current_closing_balances = (
            balance_sheet_balances
            + income_statement_balances
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

        self._current_income_statement = (
            income_statement
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

        self._current_closing_result = (
            closing_result
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

        self._current_balance_sheet = (
            balance_sheet
        )

        self._balance_sheet_frame.update_balance_sheet(
            balance_sheet
        )

    def _refresh_closing(self) -> None:
        """Aktualisiert den sichtbaren Abschlussstatus."""

        managed_fiscal_year = (
            self._workspace.managed_fiscal_year
        )

        self._closing_frame.update_fiscal_year_status(
            managed_fiscal_year.status
        )

        if self._current_closing_result is None:
            return

        self._closing_frame.update_net_income(
            self._current_closing_result.net_income
        )

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

    def _update_editing_state(self) -> None:
        """Passt die Eingabemöglichkeiten an den Geschäftsjahresstatus an."""

        enabled = self._workspace.is_open

        if enabled:
            self._opening_balance_button.state(
                ["!disabled"]
            )
        else:
            self._opening_balance_button.state(
                ["disabled"]
            )

        self._booking_frame.set_enabled(
            enabled
        )

    def _open_company_master_data(
        self,
    ) -> None:
        """Öffnet die Unternehmensstammdaten."""

        try:
            master_data = (
                self._workspace.load_company_master_data()
            )
        except ValueError as exc:
            messagebox.showerror(
                "Unternehmensstammdaten",
                str(exc),
                parent=self,
            )
            return

        dialog = CompanyMasterDataDialog(
            self,
            master_data=master_data,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.save_company_master_data(
                dialog.result
            )
        except ValueError as exc:
            messagebox.showerror(
                "Unternehmensstammdaten",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Unternehmensstammdaten",
            "Die Unternehmensstammdaten wurden gespeichert.",
            parent=self,
        )
