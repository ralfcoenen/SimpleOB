"""Dialog zum Anlegen und Bearbeiten eines Anlageguts."""

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class NewFixedAssetDialog(tk.Toplevel):
    """Erfasst oder bearbeitet ein Anlagegut."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        company_id,
        depreciation_expense_account_number: str,
        fixed_asset: FixedAsset | None = None,
        acquisition_linked: bool = False,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self._depreciation_expense_account_number = (
            depreciation_expense_account_number
        )
        self._fixed_asset = fixed_asset
        self._acquisition_linked = acquisition_linked
        self.result: FixedAsset | None = None

        self._editing = fixed_asset is not None

        self.title(
            "SimpleOB – Anlagegut bearbeiten"
            if self._editing
            else "SimpleOB – Neues Anlagegut"
        )
        self.geometry("620x570")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_ui()

        if fixed_asset is not None:
            self._populate_from_fixed_asset(
                fixed_asset
            )

            if acquisition_linked:
                self._asset_type_combobox.configure(
                    state="disabled"
                )
                self._acquisition_date_entry.configure(
                    state="disabled"
                )
                self._acquisition_cost_entry.configure(
                    state="disabled"
                )

        self.after_idle(
            self._asset_code_entry.focus_set
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
            text=(
                "Anlagegut bearbeiten"
                if self._editing
                else "Neues Anlagegut"
            ),
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

        self._asset_type_var = tk.StringVar(
            value="Betriebs- und Geschäftsausstattung"
        )
        self._asset_code_var = tk.StringVar()
        self._description_var = tk.StringVar()
        self._acquisition_date_var = tk.StringVar()
        self._acquisition_cost_var = tk.StringVar()
        self._depreciation_start_date_var = (
            tk.StringVar()
        )
        self._useful_life_months_var = (
            tk.StringVar()
        )

        ttk.Label(
            form,
            text="Anlagenart",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._asset_type_combobox = ttk.Combobox(
            form,
            textvariable=self._asset_type_var,
            values=(
                "Technische Anlagen und Maschinen",
                "Betriebs- und Geschäftsausstattung",
            ),
            state="readonly",
        )
        self._asset_type_combobox.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=7,
        )

        fields = (
            (
                "Anlagen-ID",
                self._asset_code_var,
            ),
            (
                "Bezeichnung",
                self._description_var,
            ),
            (
                "Anschaffungsdatum",
                self._acquisition_date_var,
            ),
            (
                "Anschaffungskosten",
                self._acquisition_cost_var,
            ),
            (
                "AfA-Beginn",
                self._depreciation_start_date_var,
            ),
            (
                "Nutzungsdauer in Monaten",
                self._useful_life_months_var,
            ),
        )

        for row, (
            label_text,
            variable,
        ) in enumerate(
            fields,
            start=1,
        ):
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

            entry = ttk.Entry(
                form,
                textvariable=variable,
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=7,
            )

            if variable is self._asset_code_var:
                self._asset_code_entry = entry

            if variable is self._acquisition_date_var:
                self._acquisition_date_entry = entry

            if variable is self._acquisition_cost_var:
                self._acquisition_cost_entry = entry

            if variable in (
                self._acquisition_date_var,
                self._depreciation_start_date_var,
            ):
                entry.bind(
                    "<FocusOut>",
                    lambda _event, date_var=variable: (
                        self._normalize_date_var(
                            date_var
                        )
                    ),
                )

        afa_row = len(fields) + 1

        ttk.Label(
            form,
            text="AfA-Konto",
        ).grid(
            row=afa_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        ttk.Label(
            form,
            text="4830 – Abschreibungen auf Sachanlagen",
        ).grid(
            row=afa_row,
            column=1,
            sticky="w",
            pady=7,
        )

        ttk.Label(
            container,
            text=(
                "Datum: TT.MM.JJJJ · "
                "auch TTMMJJJJ oder TTMMJJ möglich · "
                "Betrag z. B. 2400,00"
            ),
        ).pack(
            anchor="w",
            pady=(12, 0),
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
            text=(
                "Änderungen speichern"
                if self._editing
                else "Anlagegut anlegen"
            ),
            command=self._create_fixed_asset,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    def _populate_from_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Übernimmt die Werte eines bestehenden Anlageguts."""

        if fixed_asset.asset_account_number == "0200":
            asset_type = (
                "Technische Anlagen und Maschinen"
            )
        elif fixed_asset.asset_account_number == "0400":
            asset_type = (
                "Betriebs- und Geschäftsausstattung"
            )
        else:
            raise ValueError(
                "Das Anlagenkonto des Anlageguts "
                "wird vom Dialog nicht unterstützt."
            )

        self._asset_type_var.set(
            asset_type
        )
        self._asset_code_var.set(
            fixed_asset.asset_code
        )
        self._description_var.set(
            fixed_asset.description
        )
        self._acquisition_date_var.set(
            fixed_asset.acquisition_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._acquisition_cost_var.set(
            self._format_amount_for_input(
                fixed_asset.acquisition_cost
            )
        )
        self._depreciation_start_date_var.set(
            fixed_asset.depreciation_start_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._useful_life_months_var.set(
            str(
                fixed_asset.useful_life_months
            )
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
    def _parse_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(
            value
        )

    def _normalize_date_var(
        self,
        variable: tk.StringVar,
    ) -> None:
        """Normalisiert eine gültige Datumseingabe."""

        value = variable.get().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(
                value
            )
        except ValueError:
            return

        variable.set(
            normalized
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
            return Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Die Anschaffungskosten sind ungültig."
            ) from exc

    def _create_fixed_asset(self) -> None:
        """Erzeugt das neue oder geänderte Anlagegut."""

        try:
            acquisition_date = self._parse_date(
                self._acquisition_date_var.get()
            )

            depreciation_start_date = (
                self._parse_date(
                    self._depreciation_start_date_var.get()
                )
            )

            self._acquisition_date_var.set(
                acquisition_date.strftime("%d.%m.%Y")
            )
            self._depreciation_start_date_var.set(
                depreciation_start_date.strftime(
                    "%d.%m.%Y"
                )
            )

            acquisition_cost = self._parse_amount(
                self._acquisition_cost_var.get()
            )

            useful_life_months = int(
                self._useful_life_months_var.get().strip()
            )

            asset_type = self._asset_type_var.get()

            if asset_type == (
                "Technische Anlagen und Maschinen"
            ):
                position_code = (
                    "HGB.266.AKTIVA.A.II.2"
                )
                asset_account_number = "0200"

            elif asset_type == (
                "Betriebs- und Geschäftsausstattung"
            ):
                position_code = (
                    "HGB.266.AKTIVA.A.II.3"
                )
                asset_account_number = "0400"

            else:
                raise ValueError(
                    "Die Anlagenart ist ungültig."
                )

            fixed_asset_kwargs = {
                "company_id": self._company_id,
                "asset_code": self._asset_code_var.get(),
                "description": self._description_var.get(),
                "position_code": position_code,
                "asset_account_number": (
                    asset_account_number
                ),
                "depreciation_expense_account_number": (
                    self._fixed_asset.depreciation_expense_account_number
                    if self._fixed_asset is not None
                    else self._depreciation_expense_account_number
                ),
                "acquisition_date": acquisition_date,
                "acquisition_cost": acquisition_cost,
                "depreciation_start_date": (
                    depreciation_start_date
                ),
                "useful_life_months": useful_life_months,
            }

            if self._fixed_asset is not None:
                fixed_asset_kwargs.update(
                    {
                        "fixed_asset_id": (
                            self._fixed_asset.fixed_asset_id
                        ),
                        "status": (
                            self._fixed_asset.status
                        ),
                        "disposal_date": (
                            self._fixed_asset.disposal_date
                        ),
                    }
                )

            fixed_asset = FixedAsset(
                **fixed_asset_kwargs
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                (
                    "Anlagegut kann nicht bearbeitet werden"
                    if self._editing
                    else "Anlagegut kann nicht angelegt werden"
                ),
                str(exc),
                parent=self,
            )
            return

        self.result = fixed_asset
        self.destroy()
