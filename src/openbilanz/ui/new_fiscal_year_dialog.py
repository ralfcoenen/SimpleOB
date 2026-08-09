"""Dialog zum Anlegen eines neuen Geschäftsjahres."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


class NewFiscalYearDialog(tk.Toplevel):
    """Legt ein neues Geschäftsjahr für ein Unternehmen an."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        repository: CompanyRepository,
        company: Company,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._company = company

        self.result: FiscalYear | None = None

        self.title("OpenBilanz – Neues Geschäftsjahr")
        self.geometry("520x280")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_ui()
        self._set_default_dates()

        self.after_idle(
            self._start_date_entry.focus_set
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
            text="Neues Geschäftsjahr",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=self._company.name,
        ).pack(
            anchor="w",
            pady=(4, 18),
        )

        form = ttk.Frame(container)
        form.pack(
            fill="x",
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        self._start_date_var = tk.StringVar()
        self._end_date_var = tk.StringVar()

        ttk.Label(
            form,
            text="Beginn",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=8,
        )

        self._start_date_entry = ttk.Entry(
            form,
            textvariable=self._start_date_var,
            width=16,
        )
        self._start_date_entry.grid(
            row=0,
            column=1,
            sticky="w",
            pady=8,
        )

        ttk.Label(
            form,
            text="Ende",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=8,
        )

        ttk.Entry(
            form,
            textvariable=self._end_date_var,
            width=16,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=8,
        )

        ttk.Label(
            container,
            text="Datumsformat: TT.MM.JJJJ",
        ).pack(
            anchor="w",
            pady=(8, 0),
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
            text="Geschäftsjahr anlegen",
            command=self._create_fiscal_year,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    def _set_default_dates(self) -> None:
        """Schlägt das nächste Kalenderjahr vor."""

        fiscal_years = (
            self._repository.get_fiscal_years(
                self._company.company_id
            )
        )

        if fiscal_years:
            next_year = (
                fiscal_years[-1].end_date.year + 1
            )
        else:
            next_year = datetime.now().year

        self._start_date_var.set(
            f"01.01.{next_year}"
        )
        self._end_date_var.set(
            f"31.12.{next_year}"
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

    def _create_fiscal_year(self) -> None:
        """Erzeugt und speichert das Geschäftsjahr."""

        try:
            start_date = self._parse_date(
                self._start_date_var.get()
            )
            end_date = self._parse_date(
                self._end_date_var.get()
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            self._repository.add_fiscal_year(
                self._company.company_id,
                fiscal_year,
            )

        except ValueError as exc:
            messagebox.showerror(
                "Geschäftsjahr kann nicht angelegt werden",
                str(exc),
                parent=self,
            )
            return

        self.result = fiscal_year
        self.destroy()
        
    