"""Darstellung der Bilanz."""

import tkinter as tk
from decimal import Decimal
from tkinter import ttk

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.money import ZERO


class BalanceSheetFrame(ttk.Frame):
    """Stellt eine HGB-Bilanz dar."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(parent)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Bilanzdarstellung."""

        self.columnconfigure(
            0,
            weight=1,
        )
        self.columnconfigure(
            1,
            weight=1,
        )
        self.rowconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            self,
            text="Aktiva",
            font=("TkDefaultFont", 15, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=(0, 8),
        )

        ttk.Label(
            self,
            text="Passiva",
            font=("TkDefaultFont", 15, "bold"),
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(10, 0),
            pady=(0, 8),
        )

        self._assets_tree = self._create_tree(
            parent=self,
        )
        self._assets_tree.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 10),
        )

        self._liabilities_tree = self._create_tree(
            parent=self,
        )
        self._liabilities_tree.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(10, 0),
        )

        separator = ttk.Separator(
            self,
            orient="horizontal",
        )
        separator.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(14, 10),
        )

        self._totals_label = ttk.Label(
            self,
            text="Aktiva: 0,00 €   Passiva: 0,00 €",
            font=("TkDefaultFont", 12, "bold"),
        )
        self._totals_label.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="e",
        )

        self._status_label = ttk.Label(
            self,
            text="Bilanz ausgeglichen: Ja",
        )
        self._status_label.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(4, 0),
        )

    @staticmethod
    def _create_tree(
        *,
        parent: tk.Misc,
    ) -> ttk.Treeview:
        """Erzeugt eine Baumansicht für eine Bilanzseite."""

        tree = ttk.Treeview(
            parent,
            columns=("amount",),
            show="tree headings",
        )

        tree.heading(
            "#0",
            text="Position",
        )
        tree.heading(
            "amount",
            text="Betrag",
        )

        tree.column(
            "#0",
            width=330,
            anchor="w",
        )
        tree.column(
            "amount",
            width=130,
            anchor="e",
        )

        return tree

    def update_balance_sheet(
        self,
        balance_sheet: BalanceSheet,
    ) -> None:
        """Zeigt die übergebene Bilanz an."""

        self._clear_tree(
            self._assets_tree
        )
        self._clear_tree(
            self._liabilities_tree
        )

        self._insert_position(
            tree=self._assets_tree,
            parent="",
            position=balance_sheet.assets,
            balance_sheet=balance_sheet,
        )

        self._insert_position(
            tree=self._liabilities_tree,
            parent="",
            position=balance_sheet.liabilities,
            balance_sheet=balance_sheet,
        )

        assets_total = balance_sheet.amount_for(
            balance_sheet.assets
        )
        liabilities_total = balance_sheet.amount_for(
            balance_sheet.liabilities
        )

        self._totals_label.config(
            text=(
                "Aktiva: "
                f"{self._format_amount(assets_total)} €"
                "   "
                "Passiva: "
                f"{self._format_amount(liabilities_total)} €"
            )
        )

        if balance_sheet.is_balanced():
            self._status_label.config(
                text="Bilanz ausgeglichen: Ja"
            )
        else:
            difference = (
                assets_total
                - liabilities_total
            )

            self._status_label.config(
                text=(
                    "Bilanz ausgeglichen: Nein"
                    "   Differenz: "
                    f"{self._format_amount(difference)} €"
                )
            )

    def _insert_position(
        self,
        *,
        tree: ttk.Treeview,
        parent: str,
        position: FinancialStatementPosition,
        balance_sheet: BalanceSheet,
    ) -> None:
        """Fügt eine HGB-Position rekursiv ein."""

        amount = balance_sheet.amount_for(
            position
        )

        if amount == ZERO:
            return

        item_id = tree.insert(
            parent,
            "end",
            text=position.name,
            values=(
                self._format_amount(amount),
            ),
            open=True,
        )

        for child in position.children:
            self._insert_position(
                tree=tree,
                parent=item_id,
                position=child,
                balance_sheet=balance_sheet,
            )

    @staticmethod
    def _clear_tree(
        tree: ttk.Treeview,
    ) -> None:
        """Leert eine Bilanzseite."""

        for item in tree.get_children():
            tree.delete(item)

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
