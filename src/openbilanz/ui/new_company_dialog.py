"""Dialog zum Anlegen einer neuen Buchhaltung."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from uuid import uuid4

from openbilanz.core.context import ApplicationContext
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


class NewCompanyDialog(tk.Toplevel):
    """Legt ein Unternehmen mit erstem Geschäftsjahr an."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        repository: CompanyRepository,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self.result: ApplicationContext | None = None

        self.title("OpenBilanz – Neue Buchhaltung")
        self.geometry("600x330")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_ui()

        self.after_idle(
            self._company_name_entry.focus_set
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
            text="Neue Buchhaltung",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 20),
        )

        form = ttk.Frame(container)
        form.pack(
            fill="x",
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        self._company_name_var = tk.StringVar()
        self._start_date_var = tk.StringVar(
            value="01.01.2026"
        )
        self._end_date_var = tk.StringVar(
            value="31.12.2026"
        )

        ttk.Label(
            form,
            text="Unternehmen",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=8,
        )

        self._company_name_entry = ttk.Entry(
            form,
            textvariable=self._company_name_var,
        )
        self._company_name_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8,
        )

        ttk.Label(
            form,
            text="Beginn Geschäftsjahr",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=8,
        )

        ttk.Entry(
            form,
            textvariable=self._start_date_var,
            width=16,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=8,
        )

        ttk.Label(
            form,
            text="Ende Geschäftsjahr",
        ).grid(
            row=2,
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
            row=2,
            column=1,
            sticky="w",
            pady=8,
        )

        ttk.Label(
            container,
            text="Datumsformat: TT.MM.JJJJ",
        ).pack(
            anchor="w",
            pady=(10, 0),
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
            text="Buchhaltung anlegen",
            command=self._create_company,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    @staticmethod
    def _parse_date(value: str):
        """Liest ein Datum im deutschen Format."""

        return datetime.strptime(
            value.strip(),
            "%d.%m.%Y",
        ).date()

    def _create_company(self) -> None:
        """Erzeugt und speichert die neue Buchhaltung."""

        company_name = (
            self._company_name_var.get().strip()
        )

        if not company_name:
            messagebox.showerror(
                "Ungültige Eingabe",
                "Bitte geben Sie einen Unternehmensnamen ein.",
                parent=self,
            )
            return

        try:
            start_date = self._parse_date(
                self._start_date_var.get()
            )
            end_date = self._parse_date(
                self._end_date_var.get()
            )

            company = Company(
                company_id=uuid4(),
                name=company_name,
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            self._repository.add(
                company
            )
            self._repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        except ValueError as exc:
            messagebox.showerror(
                "Ungültige Eingabe",
                str(exc),
                parent=self,
            )
            return

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.destroy()
