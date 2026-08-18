"""Dialog zum Anlegen eines neuen Anlageguts."""

import tkinter as tk
from datetime import datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from openbilanz.domain.fixed_asset import FixedAsset


class NewFixedAssetDialog(tk.Toplevel):
    """Erfasst ein neues Anlagegut."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        company_id,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self.result: FixedAsset | None = None

        self.title("OpenBilanz – Neues Anlagegut")
        self.geometry("620x570")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_ui()

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
            text="Neues Anlagegut",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 18),
        )

        form = ttk.Frame(container)
        form.pack(fill="x")

        form.columnconfigure(
            1,
            weight=1,
        )

        self._asset_code_var = tk.StringVar()
        self._description_var = tk.StringVar()
        self._asset_type_var = tk.StringVar(
            value="Betriebs- und Geschäftsausstattung"
        )       
        self._acquisition_date_var = tk.StringVar()
        self._acquisition_cost_var = tk.StringVar()
        self._depreciation_start_date_var = (
            tk.StringVar()
        )
        self._useful_life_months_var = (
            tk.StringVar()
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

        asset_type_combobox = ttk.Combobox(
            form,
            textvariable=self._asset_type_var,
            values=(
                "Technische Anlagen und Maschinen",
                "Betriebs- und Geschäftsausstattung",
            ),
            state="readonly",
        )

        asset_type_combobox.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=7,
        )
        
        for row, (
            label_text,
            variable,
        ) in enumerate(fields):
            ttk.Label(
                form,
                text=label_text,
            ).grid(
                row=row+1,
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
                row=row+1,
                column=1,
                sticky="ew",
                pady=7,
            )

            if row == 0:
                self._asset_code_entry = entry

        ttk.Label(
            form,
            text="AfA-Konto",
        ).grid(
            row=len(fields) + 1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        ttk.Label(
            form,
            text="4830 – Abschreibungen auf Sachanlagen",
        ).grid(
            row=len(fields) + 1,
            column=1,
            sticky="w",
            pady=7,
        )
        
        ttk.Label(
            container,
            text=(
                "Datumsformat: TT.MM.JJJJ · "
                "Betrag z. B. 2400,00"
            ),
        ).pack(
            anchor="w",
            pady=(12, 0),
        )

        buttons = ttk.Frame(container)
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
            text="Anlagegut anlegen",
            command=self._create_fixed_asset,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    @staticmethod
    def _parse_date(
        value: str,
    ):
        """Liest ein Datum im deutschen Format."""

        return datetime.strptime(
            value.strip(),
            "%d.%m.%Y",
        ).date()

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
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Die Anschaffungskosten sind ungültig."
            ) from exc

    def _create_fixed_asset(self) -> None:
        """Erzeugt das Anlagegut."""

        try:
            acquisition_date = self._parse_date(
                self._acquisition_date_var.get()
            )

            depreciation_start_date = (
                self._parse_date(
                    self._depreciation_start_date_var.get()
                )
            )

            acquisition_cost = self._parse_amount(
                self._acquisition_cost_var.get()
            )

            useful_life_months = int(
                self._useful_life_months_var.get().strip()
            )

            asset_type = self._asset_type_var.get()

            if asset_type == "Technische Anlagen und Maschinen":
                position_code = "HGB.266.AKTIVA.A.II.2"
                asset_account_number = "0200"
            elif asset_type == "Betriebs- und Geschäftsausstattung":
                position_code = "HGB.266.AKTIVA.A.II.3"
                asset_account_number = "0400"
            else:
                raise ValueError(
                    "Die Anlagenart ist ungültig."
                )
            
            fixed_asset = FixedAsset(
                company_id=self._company_id,
                asset_code=(
                    self._asset_code_var.get()
                ),
                description=(
                    self._description_var.get()
                ),
                position_code=position_code,
                asset_account_number=asset_account_number,
                depreciation_expense_account_number="4830",
                acquisition_date=acquisition_date,
                acquisition_cost=acquisition_cost,
                depreciation_start_date=(
                    depreciation_start_date
                ),
                useful_life_months=(
                    useful_life_months
                ),
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                "Anlagegut kann nicht angelegt werden",
                str(exc),
                parent=self,
            )
            return

        self.result = fixed_asset
        self.destroy()
    