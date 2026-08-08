"""Dialog zur Erfassung der Eröffnungsbilanz."""

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.opening_balance_item import OpeningBalanceItem
from openbilanz.domain.template_account import TemplateAccount


class OpeningBalanceDialog(tk.Toplevel):
    """Erfasst die Anfangsbestände einer Buchhaltung."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(parent)

        self.title("Eröffnungsbilanz")
        self.geometry("800x500")
        self.minsize(650, 400)

        self.transient(parent)
        self.grab_set()

        self._amount_vars: list[
            tuple[AccountType, tk.StringVar]
        ] = []

        self.result: OpeningBalance | None = None

        self._amount_vars: list[
            tuple[Account, tk.StringVar]
        ] = []
        
        self._create_ui()
        self._update_totals()

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

        title = ttk.Label(
            container,
            text="Eröffnungsbilanz",
            font=("TkDefaultFont", 20, "bold"),
        )
        title.pack(
            anchor="w",
        )

        description = ttk.Label(
            container,
            text=(
                "Erfassen Sie die Anfangsbestände "
                "der Bilanzkonten."
            ),
        )
        description.pack(
            anchor="w",
            pady=(4, 16),
        )

        table = ttk.Frame(container)
        table.pack(
            fill="x",
            expand=False,
        )

        ttk.Label(
            table,
            text="Konto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 8),
        )

        ttk.Label(
            table,
            text="Bezeichnung",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(0, 8),
        )

        ttk.Label(
            table,
            text="Anfangsbestand",
        ).grid(
            row=0,
            column=2,
            sticky="e",
            pady=(0, 8),
        )

        table.columnconfigure(
            1,
            weight=1,
        )

        self._add_account_row(
            table=table,
            row=1,
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )
        self._add_account_row(
            table=table,
            row=2,
            account_number="1600",
            name="Verbindlichkeiten",
            account_type=AccountType.LIABILITY,
        )
        self._add_account_row(
            table=table,
            row=3,
            account_number="1800",
            name="Eigenkapital",
            account_type=AccountType.EQUITY,
        )

        separator = ttk.Separator(
            container,
            orient="horizontal",
        )
        separator.pack(
            fill="x",
            pady=(20, 12),
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

    def _add_account_row(
        self,
        *,
        table: ttk.Frame,
        row: int,
        account_number: str,
        name: str,
        account_type: AccountType,
    ) -> None:
        """Erzeugt eine editierbare Kontozeile."""

        account = Account(
            template=TemplateAccount(
                account_number=account_number,
                name=name,
                account_type=account_type,
            ),
        )
        
        ttk.Label(
            table,
            text=account_number,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        ttk.Label(
            table,
            text=name,
        ).grid(
            row=row,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=4,
        )

        amount_var = tk.StringVar()

        amount_var.trace_add(
            "write",
            self._on_amount_changed,
        )

        amount_entry = ttk.Entry(
            table,
            textvariable=amount_var,
            justify="right",
            width=18,
        )
        amount_entry.grid(
            row=row,
            column=2,
            sticky="e",
            pady=4,
        )

        self._amount_vars.append(
            (
                account,
                amount_var,
            )
        )

    def _on_amount_changed(
        self,
        *_args: object,
    ) -> None:
        """Reagiert auf Änderungen der Betragseingaben."""

        self._update_totals()

    def _update_totals(self) -> None:
        """Berechnet Aktiva, Passiva und Differenz neu."""

        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")

        has_invalid_value = False

        for account, amount_var in self._amount_vars:
            try:
                amount = self._parse_amount(
                    amount_var.get()
                )
            except ValueError:
                has_invalid_value = True
                continue

            if account.account_type is AccountType.ASSET:
                total_assets += amount
            elif account.account_type in (
                AccountType.LIABILITY,
                AccountType.EQUITY,
            ):
                total_liabilities += amount

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
            not has_invalid_value
            and difference == Decimal("0.00")
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
        """Erzeugt die Eröffnungsbilanz aus den Eingaben."""

        items: list[OpeningBalanceItem] = []

        for account, amount_var in self._amount_vars:
            amount = self._parse_amount(
                amount_var.get()
            )

            if amount == Decimal("0.00"):
                continue

            items.append(
                OpeningBalanceItem(
                    account=account,
                    amount=amount,
                )
            )

        opening_balance = OpeningBalance(
            items=tuple(items),
        )

        if not opening_balance.is_balanced:
            return

        self.result = opening_balance
        self.destroy()