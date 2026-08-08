"""Darstellung der Gewinn- und Verlustrechnung."""

import tkinter as tk
from decimal import Decimal
from tkinter import ttk

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.money import ZERO


class IncomeStatementFrame(ttk.Frame):
    """Stellt die laufende GuV nach § 275 HGB dar."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(parent)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die GuV-Darstellung."""

        self.columnconfigure(
            0,
            weight=1,
        )
        self.rowconfigure(
            0,
            weight=1,
        )

        self._tree = ttk.Treeview(
            self,
            columns=("amount",),
            show="tree headings",
        )

        self._tree.heading(
            "#0",
            text="Position",
        )
        self._tree.heading(
            "amount",
            text="Betrag",
        )

        self._tree.column(
            "#0",
            width=620,
            anchor="w",
        )
        self._tree.column(
            "amount",
            width=150,
            anchor="e",
        )

        self._tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        ttk.Separator(
            self,
            orient="horizontal",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(14, 10),
        )

        self._result_label = ttk.Label(
            self,
            text="Laufendes Ergebnis: 0,00 €",
            font=("TkDefaultFont", 12, "bold"),
        )
        self._result_label.grid(
            row=2,
            column=0,
            sticky="e",
        )

    def update_income_statement(
        self,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
    ) -> None:
        """Aktualisiert die GuV."""

        self._clear_tree()

        for position in (
            income_statement.income_statement.children
        ):
            self._insert_position(
                parent="",
                position=position,
                income_statement=income_statement,
            )

        if net_income > ZERO:
            description = "Jahresüberschuss"
        elif net_income < ZERO:
            description = "Jahresfehlbetrag"
        else:
            description = "Ergebnis"

        self._result_label.config(
            text=(
                f"{description}: "
                f"{self._format_amount(net_income)} €"
            )
        )

    def _insert_position(
        self,
        *,
        parent: str,
        position: FinancialStatementPosition,
        income_statement: IncomeStatement,
    ) -> None:
        """Fügt eine belegte GuV-Position ein."""

        amount = income_statement.amount_for(
            position
        )

        if amount == ZERO:
            return

        item_id = self._tree.insert(
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
                parent=item_id,
                position=child,
                income_statement=income_statement,
            )

    def _clear_tree(self) -> None:
        """Leert die GuV-Anzeige."""

        for item in self._tree.get_children():
            self._tree.delete(item)

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
