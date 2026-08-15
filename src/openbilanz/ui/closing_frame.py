"""Darstellung und Bedienung des Jahresabschlusses."""

import tkinter as tk
from collections.abc import Callable
from decimal import Decimal
from tkinter import ttk

from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.fiscal_year_status import FiscalYearStatus


class ClosingFrame(ttk.Frame):
    """Stellt Status und Aktionen des Jahresabschlusses dar."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_validate: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        self._on_validate = on_validate
        self._on_close = on_close

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        self.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            self,
            text="Jahresabschluss",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        self._fiscal_year_status_label = ttk.Label(
            self,
            text="Geschäftsjahr: Offen",
            font=("TkDefaultFont", 12, "bold"),
        )
        self._fiscal_year_status_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(14, 4),
        )

        self._result_label = ttk.Label(
            self,
            text="Jahresergebnis: noch nicht ermittelt",
        )
        self._result_label.grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 16),
        )

        ttk.Separator(
            self,
            orient="horizontal",
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 16),
        )

        ttk.Label(
            self,
            text="Plausibilitätsprüfung",
            font=("TkDefaultFont", 13, "bold"),
        ).grid(
            row=4,
            column=0,
            sticky="w",
        )

        self._consistency_status_label = ttk.Label(
            self,
            text="Noch nicht geprüft.",
        )
        self._consistency_status_label.grid(
            row=5,
            column=0,
            sticky="w",
            pady=(8, 4),
        )

        self._errors = tk.Listbox(
            self,
            height=6,
        )
        self._errors.grid(
            row=6,
            column=0,
            sticky="nsew",
            pady=(0, 12),
        )

        self.rowconfigure(
            6,
            weight=1,
        )

        buttons = ttk.Frame(
            self
        )
        buttons.grid(
            row=7,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        self._validate_button = ttk.Button(
            buttons,
            text="Abschluss prüfen",
            command=self._on_validate,
        )
        self._validate_button.pack(
            side="left",
        )

        self._close_button = ttk.Button(
            buttons,
            text="Geschäftsjahr abschließen",
            command=self._on_close,
        )
        self._close_button.pack(
            side="left",
            padx=(8, 0),
        )

        self._close_button.state(
            ["disabled"]
        )

    def update_fiscal_year_status(
        self,
        status: FiscalYearStatus,
    ) -> None:
        """Aktualisiert den Status des Geschäftsjahres."""

        if status is FiscalYearStatus.OPEN:
            text = "Geschäftsjahr: Offen"

            self._validate_button.state(
                ["!disabled"]
            )

        else:
            text = "Geschäftsjahr: Abgeschlossen"

            self._validate_button.state(
                ["disabled"]
            )

            self._close_button.state(
                ["disabled"]
            )

        self._fiscal_year_status_label.config(
            text=text
        )

    def update_net_income(
        self,
        net_income: Decimal,
    ) -> None:
        """Aktualisiert das angezeigte Jahresergebnis."""

        if net_income > Decimal("0.00"):
            description = "Jahresüberschuss"
        elif net_income < Decimal("0.00"):
            description = "Jahresfehlbetrag"
        else:
            description = "Jahresergebnis"

        self._result_label.config(
            text=(
                f"{description}: "
                f"{self._format_amount(net_income)} €"
            )
        )

    def update_consistency(
        self,
        result: ClosingConsistencyResult,
    ) -> None:
        """Zeigt das Ergebnis der Abschlussprüfung."""

        self._errors.delete(
            0,
            tk.END,
        )

        if result.is_consistent:
            self._consistency_status_label.config(
                text="Plausibilitätsprüfung erfolgreich."
            )

            self._close_button.state(
                ["!disabled"]
            )

            return

        self._consistency_status_label.config(
            text="Plausibilitätsprüfung fehlgeschlagen."
        )

        self._close_button.state(
            ["disabled"]
        )

        for error in result.errors:
            self._errors.insert(
                tk.END,
                error,
            )

    def mark_closed(self) -> None:
        """Stellt den Abschlusszustand in der Oberfläche dar."""

        self.update_fiscal_year_status(
            FiscalYearStatus.CLOSED
        )

        self._consistency_status_label.config(
            text="Geschäftsjahr wurde abgeschlossen."
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

