"""Hauptfenster der OpenBilanz-Anwendung."""
import tkinter as tk
from datetime import date
from tkinter import ttk

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.journal import Journal
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
        self.geometry("900x600")
        self.minsize(700, 450)
        self._journal = Journal()
        self._ledger = Ledger()

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number="9000",
        )
        self._posting_service = PostingService()
        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        container = ttk.Frame(
            self,
            padding=24,
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
            pady=(4, 24),
        )

        opening_balance_button = ttk.Button(
            container,
            text="Eröffnungsbilanz erfassen",
            command=self._open_opening_balance,
        )
        
        ttk.Separator(
            container,
            orient="horizontal",
        ).pack(
            fill="x",
            pady=24,
        )

        overview_title = ttk.Label(
            container,
            text="Buchhaltungsübersicht",
            font=("TkDefaultFont", 16, "bold"),
        )
        overview_title.pack(
            anchor="w",
        )

        self._journal_status = ttk.Label(
            container,
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
            container,
            columns=columns,
            show="headings",
            height=6,
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
            width=300,
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
            fill="x",
            pady=(0, 12),
)
        
        opening_balance_button.pack(
            anchor="w",
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

        self._refresh_overview()

    def _refresh_overview(self) -> None:
        """Aktualisiert die Buchhaltungsübersicht."""

        self._journal_status.config(
            text=f"Journal: {len(self._journal)} Buchungen"
        )

        for item in self._account_table.get_children():
            self._account_table.delete(item)

        accounts = (
            ("1200", "Bank"),
            ("1600", "Verbindlichkeiten"),
            ("1800", "Eigenkapital"),
            ("9000", "Eröffnungsbilanzkonto"),
        )

        for account_number, name in accounts:
            account = self._ledger.get_account(
                account_number
            )

            self._account_table.insert(
                "",
                "end",
                values=(
                    account_number,
                    name,
                    self._format_amount(account.debit),
                    self._format_amount(account.credit),
                ),
            )

    @staticmethod
    def _format_amount(amount: object) -> str:
        """Formatiert einen Geldbetrag für die Anzeige."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
