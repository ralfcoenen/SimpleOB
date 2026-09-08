"""Dialog zur Erfassung einer steuerlichen AfA-Abweichung."""

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)


class TaxDepreciationAdjustmentDialog(tk.Toplevel):
    """Erfasst die steuerliche AfA zu einer bestätigten HGB-Abschreibung."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        fixed_asset: FixedAsset,
        depreciation: FixedAssetDepreciation,
        initial_tax_amount: Decimal,
    ) -> None:
        super().__init__(parent)

        self._fixed_asset = fixed_asset
        self._depreciation = depreciation

        self.result: Decimal | None = None

        self.title(
            "SimpleOB – Steuerliche AfA-Abweichung"
        )
        self.geometry("560x360")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._tax_amount_var = tk.StringVar(
            value=self._format_amount_for_input(
                initial_tax_amount
            )
        )
        self._difference_var = tk.StringVar()

        self._create_ui()
        self._update_difference()

        self.after_idle(
            self._tax_amount_entry.focus_set
        )

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

        ttk.Label(
            container,
            text="Steuerliche AfA-Abweichung",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 18),
        )

        form = ttk.Frame(
            container
        )
        form.pack(
            fill="x"
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        rows = (
            (
                "Anlagegut",
                (
                    f"{self._fixed_asset.asset_code} – "
                    f"{self._fixed_asset.description}"
                ),
            ),
            (
                "Abschreibungsdatum",
                self._depreciation.depreciation_date.strftime(
                    "%d.%m.%Y"
                ),
            ),
            (
                "HGB-AfA",
                (
                    f"{self._format_amount_for_display(
                        self._depreciation.amount
                    )} €"
                ),
            ),
        )

        for row, (
            label_text,
            value_text,
        ) in enumerate(rows):
            ttk.Label(
                form,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=7,
            )

            ttk.Label(
                form,
                text=value_text,
            ).grid(
                row=row,
                column=1,
                sticky="w",
                pady=7,
            )

        tax_row = len(rows)

        ttk.Label(
            form,
            text="Steuerliche AfA",
        ).grid(
            row=tax_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._tax_amount_entry = ttk.Entry(
            form,
            textvariable=self._tax_amount_var,
        )
        self._tax_amount_entry.grid(
            row=tax_row,
            column=1,
            sticky="ew",
            pady=7,
        )
        self._tax_amount_entry.bind(
            "<KeyRelease>",
            self._on_tax_amount_changed,
        )

        difference_row = tax_row + 1

        ttk.Label(
            form,
            text="Differenz",
        ).grid(
            row=difference_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        ttk.Label(
            form,
            textvariable=self._difference_var,
        ).grid(
            row=difference_row,
            column=1,
            sticky="w",
            pady=7,
        )

        ttk.Label(
            container,
            text=(
                "Nur abweichende steuerliche AfA erfassen. "
                "Entspricht die steuerliche AfA der HGB-AfA, "
                "wird keine Abweichung gespeichert."
            ),
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(18, 0),
        )

        buttons = ttk.Frame(
            container
        )
        buttons.pack(
            fill="x",
            side="bottom",
        )

        ttk.Button(
            buttons,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
        )

        ttk.Button(
            buttons,
            text="Speichern",
            command=self._save,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    @staticmethod
    def _format_amount_for_input(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für das Eingabefeld."""

        return format(
            value,
            ".2f",
        ).replace(
            ".",
            ",",
        )

    @staticmethod
    def _format_amount_for_display(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für die Anzeige."""

        return format(
            value,
            ".2f",
        ).replace(
            ".",
            ",",
        )

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Liest einen Geldbetrag."""

        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            amount = Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Die steuerliche AfA ist ungültig."
            ) from exc

        if amount < Decimal("0.00"):
            raise ValueError(
                "Die steuerliche AfA darf nicht negativ sein."
            )

        return amount

    def _on_tax_amount_changed(
        self,
        _event=None,
    ) -> None:
        """Aktualisiert die angezeigte Differenz."""

        self._update_difference()

    def _update_difference(self) -> None:
        """Berechnet die Differenz zur HGB-AfA."""

        try:
            tax_amount = self._parse_amount(
                self._tax_amount_var.get()
            )
        except ValueError:
            self._difference_var.set(
                "–"
            )
            return

        difference = (
            tax_amount
            - self._depreciation.amount
        )

        self._difference_var.set(
            (
                f"{self._format_amount_for_display(
                    difference
                )} €"
            )
        )

    def _save(self) -> None:
        """Übernimmt die eingegebene steuerliche AfA."""

        try:
            tax_amount = self._parse_amount(
                self._tax_amount_var.get()
            )
        except ValueError as exc:
            messagebox.showerror(
                "Steuerliche AfA-Abweichung",
                str(exc),
                parent=self,
            )
            return

        self.result = tax_amount
        self.destroy()
