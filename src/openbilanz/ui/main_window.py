"""Hauptfenster der OpenBilanz-Anwendung."""

import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import ttk

from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account import Account
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
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
from openbilanz.services.opening_balance_service import (
    OpeningBalanceService,
)
from openbilanz.services.posting_service import PostingService
from openbilanz.ui.opening_balance_dialog import (
    OpeningBalanceDialog,
)


class MainWindow(tk.Tk):
    """Hauptfenster von OpenBilanz."""

    def __init__(self) -> None:
        super().__init__()

        self.title("OpenBilanz")
        self.geometry("950x650")
        self.minsize(750, 500)

        self._journal = Journal()
        self._ledger = Ledger()

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number="9000",
        )
        self._posting_service = PostingService()

        self._accounts = self._load_standard_accounts()

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in self._accounts
        }

        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

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

        title = ttk.Label(
            container,
            text="OpenBilanz",
            font=("TkDefaultFont", 24, "bold"),
        )
        title.pack(
            anchor="w",
        )

        subtitle = ttk.Label(
            container,
            text="Buchhaltung und Jahresabschluss",
        )
        subtitle.pack(
            anchor="w",
            pady=(4, 16),
        )

        opening_balance_button = ttk.Button(
            container,
            text="Eröffnungsbilanz erfassen",
            command=self._open_opening_balance,
        )
        opening_balance_button.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._notebook = ttk.Notebook(container)
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

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        title = ttk.Label(
            self._accounts_tab,
            text="Kontenübersicht",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(
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

        self._account_table.column(
            "account_number",
            width=100,
            anchor="w",
        )
        self._account_table.column(
            "name",
            width=350,
            anchor="w",
        )
        self._account_table.column(
            "debit",
            width=140,
            anchor="e",
        )
        self._account_table.column(
            "credit",
            width=140,
            anchor="e",
        )

        self._account_table.pack(
            fill="both",
            expand=True,
        )

    def _create_journal_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Journal."""

        title = ttk.Label(
            self._journal_tab,
            text="Journal",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(
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

        title = ttk.Label(
            self._booking_tab,
            text="Neue Buchung",
            font=("TkDefaultFont", 16, "bold"),
        )
        title.pack(
            anchor="w",
            pady=(0, 16),
        )

        form = ttk.Frame(self._booking_tab)
        form.pack(
            fill="x",
            anchor="nw",
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        self._booking_date_var = tk.StringVar(
            value=date.today().strftime("%d.%m.%Y")
        )
        self._booking_description_var = tk.StringVar()
        self._debit_account_var = tk.StringVar()
        self._credit_account_var = tk.StringVar()
        self._booking_amount_var = tk.StringVar()
        self._booking_status_var = tk.StringVar()

        ttk.Label(
            form,
            text="Datum",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        ttk.Entry(
            form,
            textvariable=self._booking_date_var,
            width=16,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=6,
        )

        ttk.Label(
            form,
            text="Buchungstext",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        ttk.Entry(
            form,
            textvariable=self._booking_description_var,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            form,
            text="Sollkonto",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._debit_account_box = ttk.Combobox(
            form,
            textvariable=self._debit_account_var,
            values=self._account_display_names,
        )
        self._debit_account_box.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            form,
            text="Habenkonto",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._credit_account_box = ttk.Combobox(
            form,
            textvariable=self._credit_account_var,
            values=self._account_display_names,
        )
        self._credit_account_box.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            form,
            text="Betrag",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        ttk.Entry(
            form,
            textvariable=self._booking_amount_var,
            justify="right",
            width=18,
        ).grid(
            row=4,
            column=1,
            sticky="w",
            pady=6,
        )

        self._booking_button = ttk.Button(
            form,
            text="Buchung übernehmen",
            command=self._book,
        )
        self._booking_button.grid(
            row=5,
            column=1,
            sticky="e",
            pady=(18, 6),
        )
        self._booking_button.state(
            ["disabled"]
        )

        ttk.Label(
            form,
            textvariable=self._booking_status_var,
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        variables = (
            self._booking_date_var,
            self._booking_description_var,
            self._debit_account_var,
            self._credit_account_var,
            self._booking_amount_var,
        )

        for variable in variables:
            variable.trace_add(
                "write",
                self._on_booking_form_changed,
            )


    def _open_opening_balance(self) -> None:
        """Erfasst und verbucht die Eröffnungsbilanz."""

        dialog = OpeningBalanceDialog(self)

        self.wait_window(dialog)

        if dialog.result is None:
            return

        bookings = self._opening_balance_service.create_bookings(
            opening_balance=dialog.result,
            booking_date=date.today(),
        )

        for booking in bookings:
            self._posting_service.post_booking(
                booking=booking,
                ledger=self._ledger,
                journal=self._journal,
            )

        self._refresh_all()

    def _book(self) -> None:
        """Erzeugt und verbucht eine laufende Buchung."""

        debit_account = self._resolve_account(
            self._debit_account_var.get()
        )
        credit_account = self._resolve_account(
            self._credit_account_var.get()
        )

        if (
            debit_account is None
            or credit_account is None
        ):
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date_var.get()
            )
            amount = self._parse_amount(
                self._booking_amount_var.get()
            )
        except ValueError:
            return

        description = (
            self._booking_description_var.get().strip()
        )

        booking = Booking(
            booking_date=booking_date,
            description=description,
            lines=(
                BookingLine(
                    account_number=debit_account.number,
                    side=EntrySide.DEBIT,
                    amount=amount,
                ),
                BookingLine(
                    account_number=credit_account.number,
                    side=EntrySide.CREDIT,
                    amount=amount,
                ),
            ),
        )

        self._posting_service.post_booking(
            booking=booking,
            ledger=self._ledger,
            journal=self._journal,
        )

        self._refresh_all()
        self._clear_booking_form()

        self._booking_status_var.set(
            "Buchung wurde übernommen."
        )

    def _on_booking_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft, ob die Buchungsmaske vollständig ist."""

        debit_account = self._resolve_account(
            self._debit_account_var.get()
        )
        credit_account = self._resolve_account(
            self._credit_account_var.get()
        )

        valid = True

        try:
            self._parse_booking_date(
                self._booking_date_var.get()
            )
            self._parse_amount(
                self._booking_amount_var.get()
            )
        except ValueError:
            valid = False

        if not self._booking_description_var.get().strip():
            valid = False

        if debit_account is None:
            valid = False

        if credit_account is None:
            valid = False

        if (
            debit_account is not None
            and credit_account is not None
            and debit_account.number == credit_account.number
        ):
            valid = False

        if valid:
            self._booking_button.state(
                ["!disabled"]
            )
        else:
            self._booking_button.state(
                ["disabled"]
            )

        self._booking_status_var.set("")

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt ein Konto aus einer Benutzereingabe."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = self._accounts_by_display_name.get(
            normalized
        )

        if direct_match is not None:
            return direct_match

        number_matches = tuple(
            account
            for account in self._accounts
            if account.number == normalized
        )

        if len(number_matches) == 1:
            return number_matches[0]

        search_value = normalized.casefold()

        text_matches = tuple(
            account
            for account in self._accounts
            if search_value
            in self._account_display_name(account).casefold()
        )

        if len(text_matches) == 1:
            return text_matches[0]

        return None

    def _clear_booking_form(self) -> None:
        """Leert die Buchungsmaske nach erfolgreicher Buchung."""

        self._booking_description_var.set("")
        self._debit_account_var.set("")
        self._credit_account_var.set("")
        self._booking_amount_var.set("")

    def _refresh_all(self) -> None:
        """Aktualisiert alle sichtbaren Buchhaltungsdaten."""

        self._refresh_overview()
        self._refresh_journal()
        self.update_idletasks()

    def _refresh_overview(self) -> None:
        """Aktualisiert die Kontenübersicht."""

        self._journal_status.config(
            text=f"Journal: {len(self._journal)} Buchungen"
        )

        for item in self._account_table.get_children():
            self._account_table.delete(item)

        for account in self._accounts:
            debit = ZERO
            credit = ZERO

            try:
                ledger_account = self._ledger.get_account(
                    account.number
                )
            except KeyError:
                pass
            else:
                debit = ledger_account.debit
                credit = ledger_account.credit

            self._account_table.insert(
                "",
                "end",
                values=(
                    account.number,
                    account.name,
                    self._format_amount(debit),
                    self._format_amount(credit),
                ),
            )

        try:
            opening_account = self._ledger.get_account(
                "9000"
            )
        except KeyError:
            return

        self._account_table.insert(
            "",
            "end",
            values=(
                "9000",
                "Eröffnungsbilanzkonto",
                self._format_amount(opening_account.debit),
                self._format_amount(opening_account.credit),
            ),
        )
    
    def _refresh_journal(self) -> None:
        """Aktualisiert die Journalanzeige."""

        for item in self._journal_table.get_children():
            self._journal_table.delete(item)

        for booking in self._journal:
            for debit_account, credit_account, amount in (
                self._posting_service._pair_lines(booking)
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
                        self._format_amount(amount),
                    ),
                )

    def _load_standard_accounts(
        self,
    ) -> tuple[Account, ...]:
        """Lädt den OpenBilanz-Standardkontenrahmen."""

        assets, liabilities = (
            create_hgb_balance_sheet_structure()
        )
        income_statement = (
            create_hgb_income_statement_structure()
        )

        provider = HgbFinancialStatementPositionProvider(
            (
                assets,
                liabilities,
                income_statement,
            ),
        )

        csv_file = (
            Path(__file__).resolve().parent.parent
            / "resources"
            / "chart_of_accounts"
            / "openbilanz_standard.csv"
        )

        template = CsvChartOfAccountsImporter(
            position_provider=provider,
        ).load(csv_file)

        return tuple(
            Account(template=template_account)
            for template_account in template.accounts
        )

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die Kontendarstellung der GUI."""

        return (
            f"{account.number} – "
            f"{account.name}"
        )

    @staticmethod
    def _parse_booking_date(
        value: str,
    ) -> date:
        """Wandelt ein deutsches Datum in date um."""

        try:
            return datetime.strptime(
                value.strip(),
                "%d.%m.%Y",
            ).date()
        except ValueError as exc:
            raise ValueError(
                "Ungültiges Buchungsdatum."
            ) from exc

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt einen deutschen Geldbetrag in Decimal um."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

        normalized = normalized.replace(
            ".",
            "",
        )
        normalized = normalized.replace(
            ",",
            ".",
        )

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Geldbetrag."
            ) from exc

        if amount <= ZERO:
            raise ValueError(
                "Der Buchungsbetrag muss größer als 0,00 sein."
            )

        return amount.quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _format_amount(
        amount: object,
    ) -> str:
        """Formatiert einen Geldbetrag für die Anzeige."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
