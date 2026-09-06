"""Dialog zur Pflege der Unternehmensstammdaten."""

import tkinter as tk
from tkinter import messagebox, ttk

from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)

FEDERAL_STATES = (
    ("BW", "Baden-Württemberg"),
    ("BY", "Bayern"),
    ("BE", "Berlin"),
    ("BB", "Brandenburg"),
    ("HB", "Bremen"),
    ("HH", "Hamburg"),
    ("HE", "Hessen"),
    ("MV", "Mecklenburg-Vorpommern"),
    ("NI", "Niedersachsen"),
    ("NW", "Nordrhein-Westfalen"),
    ("RP", "Rheinland-Pfalz"),
    ("SL", "Saarland"),
    ("SN", "Sachsen"),
    ("ST", "Sachsen-Anhalt"),
    ("SH", "Schleswig-Holstein"),
    ("TH", "Thüringen"),
)

FEDERAL_STATE_LABELS = {
    code: name
    for code, name in FEDERAL_STATES
}

FEDERAL_STATE_CODES = {
    name: code
    for code, name in FEDERAL_STATES
}

class CompanyMasterDataDialog(tk.Toplevel):
    """Bearbeitet die Stammdaten eines Unternehmens."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        master_data: CompanyMasterData,
    ) -> None:
        super().__init__(parent)

        self._master_data = master_data
        self.result: CompanyMasterData | None = None

        self.title(
            "SimpleOB – Unternehmensstammdaten"
        )
        self.geometry("760x760")
        self.minsize(700, 700)

        self.transient(parent)
        self.grab_set()

        self._create_ui()
        self._load_values()

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
            text="Unternehmensstammdaten",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=self._master_data.company.name,
        ).pack(
            anchor="w",
            pady=(4, 18),
        )
        ttk.Label(
            container,
            text="* Pflichtfeld für die E-Bilanz",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        form = ttk.Frame(
            container
        )
        form.pack(
            fill="both",
            expand=True,
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        self._legal_form_var = tk.StringVar()
        self._tax_number_var = tk.StringVar()
        self._tax_office_var = tk.StringVar()
        self._tax_id_var = tk.StringVar()
        self._tax_economic_id_var = tk.StringVar()
        self._bf4_var = tk.StringVar()
        self._street_var = tk.StringVar()
        self._house_number_var = tk.StringVar()
        self._postal_code_var = tk.StringVar()
        self._city_var = tk.StringVar()
        self._country_var = tk.StringVar()
        self._federal_state_var = tk.StringVar()
        self._business_var = tk.StringVar()

        fields = (
            (
                "Rechtsform *",
                self._legal_form_var,
            ),
            (
                "Steuernummer *",
                self._tax_number_var,
            ),
            (
                "Finanzamt",
                self._tax_office_var,
            ),
            (
                "Steuer-ID",
                self._tax_id_var,
            ),
            (
                "Wirtschafts-ID",
                self._tax_economic_id_var,
            ),
            (
                "BF4",
                self._bf4_var,
            ),
            (
                "Straße *",
                self._street_var,
            ),
            (
                "Hausnummer *",
                self._house_number_var,
            ),
            (
                "PLZ *",
                self._postal_code_var,
            ),
            (
                "Ort *",
                self._city_var,
            ),
            (
                "Land *",
                self._country_var,
            ),
            (
                "Geschäftstätigkeit *",
                self._business_var,
            ),
        )

        for row, (label, variable) in enumerate(
            fields
        ):
            ttk.Label(
                form,
                text=label,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=6,
            )

            ttk.Entry(
                form,
                textvariable=variable,
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=6,
            )

        federal_state_row = len(fields)

        ttk.Label(
            form,
            text="Bundesland *",
        ).grid(
            row=federal_state_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._federal_state_box = ttk.Combobox(
            form,
            textvariable=self._federal_state_var,
            values=tuple(
                name
                for _, name in FEDERAL_STATES
            ),
            state="readonly",
        )

        self._federal_state_box.grid(
            row=federal_state_row,
            column=1,
            sticky="ew",
            pady=6,
        )

        buttons = ttk.Frame(
            container
        )
        buttons.pack(
            fill="x",
            pady=(18, 0),
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

    def _load_values(self) -> None:
        """Übernimmt die vorhandenen Stammdaten."""

        self._legal_form_var.set(
            self._master_data.legal_form
        )
        self._tax_number_var.set(
            self._master_data.tax_number
        )
        self._tax_office_var.set(
            self._master_data.tax_office
        )
        self._tax_id_var.set(
            self._master_data.tax_id
        )
        self._tax_economic_id_var.set(
            self._master_data.tax_economic_id
        )
        self._bf4_var.set(
            self._master_data.bf4
        )
        self._street_var.set(
            self._master_data.street
        )
        self._house_number_var.set(
            self._master_data.house_number
        )
        self._postal_code_var.set(
            self._master_data.postal_code
        )
        self._city_var.set(
            self._master_data.city
        )
        self._country_var.set(
            self._master_data.country
        )
        self._federal_state_var.set(
            FEDERAL_STATE_LABELS.get(
                self._master_data.federal_state,
                "",
            )
        )
        self._business_var.set(
            self._master_data.business
        )

    def _save(self) -> None:
        """Erzeugt die geänderten Stammdaten."""

        try:
            master_data = CompanyMasterData(
                company=self._master_data.company,
                legal_form=self._value(
                    self._legal_form_var
                ),
                tax_number=self._value(
                    self._tax_number_var
                ),
                tax_office=self._value(
                    self._tax_office_var
                ),
                tax_id=self._value(
                    self._tax_id_var
                ),
                tax_economic_id=self._value(
                    self._tax_economic_id_var
                ),
                bf4=self._value(
                    self._bf4_var
                ),
                street=self._value(
                    self._street_var
                ),
                house_number=self._value(
                    self._house_number_var
                ),
                postal_code=self._value(
                    self._postal_code_var
                ),
                city=self._value(
                    self._city_var
                ),
                country=self._value(
                    self._country_var
                ),
                federal_state=FEDERAL_STATE_CODES.get(
                    self._value(
                        self._federal_state_var
                    ),
                    "",
                ),
                business=self._value(
                    self._business_var
                ),
            )

            master_data.validate_e_bilanz_ready()


        except (TypeError, ValueError) as exc:
            messagebox.showerror(
                "Ungültige Stammdaten",
                str(exc),
                parent=self,
            )
            return

        self.result = master_data
        self.destroy()

    @staticmethod
    def _value(
        variable: tk.StringVar,
    ) -> str:
        """Liefert einen bereinigten Eingabewert."""

        return variable.get().strip()
