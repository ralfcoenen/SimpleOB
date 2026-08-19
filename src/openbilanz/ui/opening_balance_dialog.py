"""Dialog zur Erfassung der Eröffnungsbilanz."""

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.opening_balance_item import OpeningBalanceItem


class OpeningBalanceDialog(tk.Toplevel):
    """Erfasst die Anfangsbestände einer Buchhaltung."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        accounts: tuple[Account, ...],
        excluded_account_numbers: set[str],
    ) -> None:
        super().__init__(parent)

        self.title("Eröffnungsbilanz")
        self.geometry("800x550")
        self.minsize(650, 450)

        self.transient(parent)
        self.grab_set()

        self._accounts = self._filter_accounts(
            accounts=accounts,
            excluded_account_numbers=excluded_account_numbers,
        )

        self._accounts_by_display = {
            str(account): account
            for account in self._accounts
        }

        self._items: list[OpeningBalanceItem] = []

        self._account_var = tk.StringVar()
        self._amount_var = tk.StringVar()

        self.result: OpeningBalance | None = None

        self._create_ui()
        self._update_totals()

    @staticmethod
    def _filter_accounts(
        *,
        accounts: tuple[Account, ...],
        excluded_account_numbers: set[str],
    ) -> tuple[Account, ...]:
        """Filtert die für die Eröffnungsbilanz zulässigen Konten."""

        return tuple(
            account
            for account in accounts
            if account.is_active
            and account.number not in excluded_account_numbers
            and account.account_type
            in (
                AccountType.ASSET,
                AccountType.LIABILITY,
                AccountType.EQUITY,
            )
        )

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        container = ttk.Frame(
            self,
            padding=20,
        )
        container.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            container,
            text="Eröffnungsbilanz",
            font=("TkDefaultFont", 20, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=(
                "Erfassen Sie nur die Konten, "
                "für die ein Anfangsbestand vorhanden ist."
            ),
        ).pack(
            anchor="w",
            pady=(4, 16),
        )

        entry_frame = ttk.Frame(container)
        entry_frame.pack(
            fill="x",
        )

        ttk.Label(
            entry_frame,
            text="Konto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
        )

        ttk.Label(
            entry_frame,
            text="Anfangsbestand",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 12),
        )

        self._account_combo = ttk.Combobox(
            entry_frame,
            textvariable=self._account_var,
            values=tuple(
                str(account)
                for account in self._accounts
            ),
            state="readonly",
        )
        self._account_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 12),
            pady=(4, 0),
        )

        self._amount_entry = ttk.Entry(
            entry_frame,
            textvariable=self._amount_var,
            justify="right",
            width=18,
        )
        self._amount_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(4, 0),
        )

        ttk.Button(
            entry_frame,
            text="Hinzufügen",
            command=self._add_item,
        ).grid(
            row=1,
            column=2,
            sticky="e",
            pady=(4, 0),
        )

        entry_frame.columnconfigure(
            0,
            weight=1,
        )

        self._item_table = ttk.Treeview(
            container,
            columns=(
                "account",
                "name",
                "amount",
            ),
            show="headings",
            height=10,
        )

        self._item_table.heading(
            "account",
            text="Konto",
        )
        self._item_table.heading(
            "name",
            text="Bezeichnung",
        )
        self._item_table.heading(
            "amount",
            text="Anfangsbestand",
        )

        self._item_table.column(
            "account",
            width=100,
            anchor="w",
        )
        self._item_table.column(
            "name",
            width=350,
            anchor="w",
        )
        self._item_table.column(
            "amount",
            width=150,
            anchor="e",
        )

        self._item_table.pack(
            fill="both",
            expand=True,
            pady=(16, 8),
        )

        ttk.Button(
            container,
            text="Position entfernen",
            command=self._remove_item,
        ).pack(
            anchor="w",
        )

        ttk.Separator(
            container,
            orient="horizontal",
        ).pack(
            fill="x",
            pady=(16, 12),
        )

        summary = ttk.Frame(container)
        summary.pack(
            fill="x",
        )

        self._assets_label = ttk.Label(
            summary,
            text="Aktiva: 0,00 €",
        )
        self._assets_label.pack(
            anchor="e",
        )

        self._liabilities_label = ttk.Label(
            summary,
            text="Passiva: 0,00 €",
        )
        self._liabilities_label.pack(
            anchor="e",
        )

        self._difference_label = ttk.Label(
            summary,
            text="Differenz: 0,00 €",
        )
        self._difference_label.pack(
            anchor="e",
        )

        buttons = ttk.Frame(container)
        buttons.pack(
            fill="x",
            pady=(20, 0),
        )

        ttk.Button(
            buttons,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
        )

        self._accept_button = ttk.Button(
            buttons,
            text="Übernehmen",
            command=self._accept,
        )
        self._accept_button.pack(
            side="right",
            padx=(0, 8),
        )

    def _add_item(self) -> None:
        """Fügt eine Eröffnungsposition hinzu."""

        account_display = self._account_var.get().strip()

        if not account_display:
            messagebox.showerror(
                "Eröffnungsbilanz",
                "Bitte wählen Sie ein Konto aus.",
                parent=self,
            )
            return

        account = self._accounts_by_display[account_display]

        if any(
            item.account.number == account.number
            for item in self._items
        ):
            messagebox.showerror(
                "Eröffnungsbilanz",
                "Das Konto wurde bereits erfasst.",
                parent=self,
            )
            return

        try:
            amount = self._parse_amount(
                self._amount_var.get()
            )
        except ValueError as exc:
            messagebox.showerror(
                "Eröffnungsbilanz",
                str(exc),
                parent=self,
            )
            return

        if amount == Decimal("0.00"):
            messagebox.showerror(
                "Eröffnungsbilanz",
                "Der Anfangsbestand muss größer als 0,00 € sein.",
                parent=self,
            )
            return

        item = OpeningBalanceItem(
            account=account,
            amount=amount,
        )

        self._items.append(item)

        self._item_table.insert(
            "",
            "end",
            iid=account.number,
            values=(
                account.number,
                account.name,
                self._format_amount(amount),
            ),
        )

        self._account_var.set("")
        self._amount_var.set("")

        self._update_totals()

    def _remove_item(self) -> None:
        """Entfernt die ausgewählte Eröffnungsposition."""

        selection = self._item_table.selection()

        if not selection:
            return

        account_numbers = set(selection)

        self._items = [
            item
            for item in self._items
            if item.account.number not in account_numbers
        ]

        for item_id in selection:
            self._item_table.delete(item_id)

        self._update_totals()

    def _update_totals(self) -> None:
        """Berechnet Aktiva, Passiva und Differenz neu."""

        opening_balance = OpeningBalance(
            items=tuple(self._items),
        )

        total_assets = opening_balance.total_assets
        total_liabilities = (
            opening_balance.total_liabilities_and_equity
        )
        difference = (
            total_assets
            - total_liabilities
        )

        self._assets_label.config(
            text=(
                "Aktiva: "
                f"{self._format_amount(total_assets)} €"
            )
        )

        self._liabilities_label.config(
            text=(
                "Passiva: "
                f"{self._format_amount(total_liabilities)} €"
            )
        )

        self._difference_label.config(
            text=(
                "Differenz: "
                f"{self._format_amount(difference)} €"
            )
        )

        if (
            self._items
            and opening_balance.is_balanced
        ):
            self._accept_button.state(
                ["!disabled"]
            )
        else:
            self._accept_button.state(
                ["disabled"]
            )

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt eine deutsche Betragseingabe in Decimal um."""

        normalized = value.strip()

        if not normalized:
            return Decimal("0.00")

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

        if amount < Decimal("0.00"):
            raise ValueError(
                "Negative Beträge sind nicht zulässig."
            )

        return amount.quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag deutsch."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _accept(self) -> None:
        """Übernimmt die erfasste Eröffnungsbilanz."""

        opening_balance = OpeningBalance(
            items=tuple(self._items),
        )

        if not opening_balance.is_balanced:
            return

        self.result = opening_balance
        self.destroy()