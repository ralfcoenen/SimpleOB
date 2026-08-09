"""Startdialog für OpenBilanz."""

import tkinter as tk
from tkinter import ttk

from openbilanz.core.context import ApplicationContext
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.new_company_dialog import (
    NewCompanyDialog,
)
from openbilanz.ui.new_fiscal_year_dialog import (
    NewFiscalYearDialog,
)


class StartDialog(tk.Toplevel):
    """Wählt Unternehmen und Geschäftsjahr für die Buchhaltung."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        repository: CompanyRepository,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self.result: ApplicationContext | None = None

        self.title("OpenBilanz – Buchhaltung öffnen")
        self.geometry("600x320")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._companies: tuple[Company, ...] = ()
        self._company_by_display_name: dict[str, Company] = {}
        self._fiscal_year_by_display_name: dict[
            str,
            FiscalYear,
        ] = {}

        self._create_ui()
        self._load_companies()

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
            text="OpenBilanz",
            font=("TkDefaultFont", 22, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text="Buchhaltung öffnen",
            font=("TkDefaultFont", 14, "bold"),
        ).pack(
            anchor="w",
            pady=(6, 22),
        )

        form = ttk.Frame(container)
        form.pack(
            fill="x",
        )

        form.columnconfigure(
            1,
            weight=1,
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

        self._company_var = tk.StringVar()

        self._company_box = ttk.Combobox(
            form,
            textvariable=self._company_var,
            state="readonly",
        )
        self._company_box.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=8,
        )
        self._company_box.bind(
            "<<ComboboxSelected>>",
            self._on_company_selected,
        )

        ttk.Label(
            form,
            text="Geschäftsjahr",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=8,
        )

        self._fiscal_year_var = tk.StringVar()

        self._fiscal_year_box = ttk.Combobox(
            form,
            textvariable=self._fiscal_year_var,
            state="readonly",
        )
        self._fiscal_year_box.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=8,
        )

        self._status_var = tk.StringVar()

        ttk.Label(
            container,
            textvariable=self._status_var,
        ).pack(
            anchor="w",
            pady=(16, 0),
        )

        buttons = ttk.Frame(container)
        buttons.pack(
            fill="x",
            side="bottom",
        )

        ttk.Button(
            buttons,
            text="Neue Buchhaltung anlegen",
            command=self._create_new_company,
        ).pack(
            side="left",
        )
        
        self._new_fiscal_year_button = ttk.Button(
            buttons,
            text="Neues Geschäftsjahr",
            command=self._create_new_fiscal_year,
        )
        self._new_fiscal_year_button.pack(
            side="left",
            padx=(8, 0),
        )
        self._new_fiscal_year_button.state(
            ["disabled"]
        )
        
        ttk.Button(
            buttons,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
        )

        self._open_button = ttk.Button(
            buttons,
            text="Öffnen",
            command=self._open,
        )
        self._open_button.pack(
            side="right",
            padx=(0, 8),
        )
        self._open_button.state(
            ["disabled"]
        )

    def _load_companies(self) -> None:
        """Lädt die vorhandenen Unternehmen."""

        self._companies = (
            self._repository.list_companies()
        )

        self._company_by_display_name = {
            company.name: company
            for company in self._companies
        }

        company_names = tuple(
            self._company_by_display_name
        )

        self._company_box.configure(
            values=company_names,
        )

        if not company_names:
            self._status_var.set(
                "Es ist noch keine Buchhaltung vorhanden."
            )
            return
        
        self._new_fiscal_year_button.state(
            ["!disabled"]
        )

        first_company_name = company_names[0]

        self._company_var.set(
            first_company_name
        )

        self._load_fiscal_years(
            self._company_by_display_name[
                first_company_name
            ]
        )

    def _on_company_selected(
        self,
        _event: tk.Event,
    ) -> None:
        """Lädt die Geschäftsjahre des ausgewählten Unternehmens."""

        company = self._selected_company()

        if company is None:
            return

        self._load_fiscal_years(
            company
        )

    def _load_fiscal_years(
        self,
        company: Company,
    ) -> None:
        """Lädt die Geschäftsjahre eines Unternehmens."""

        fiscal_years = (
            self._repository.get_fiscal_years(
                company.company_id
            )
        )

        self._fiscal_year_by_display_name = {
            fiscal_year.display_name: fiscal_year
            for fiscal_year in fiscal_years
        }

        display_names = tuple(
            self._fiscal_year_by_display_name
        )

        self._fiscal_year_box.configure(
            values=display_names,
        )

        if not display_names:
            self._fiscal_year_var.set("")
            self._open_button.state(
                ["disabled"]
            )
            self._status_var.set(
                "Für dieses Unternehmen ist "
                "noch kein Geschäftsjahr vorhanden."
            )
            return

        self._fiscal_year_var.set(
            display_names[0]
        )

        self._status_var.set("")
        self._open_button.state(
            ["!disabled"]
        )

    def _selected_company(
        self,
    ) -> Company | None:
        """Liefert das ausgewählte Unternehmen."""

        return self._company_by_display_name.get(
            self._company_var.get()
        )

    def _selected_fiscal_year(
        self,
    ) -> FiscalYear | None:
        """Liefert das ausgewählte Geschäftsjahr."""

        return self._fiscal_year_by_display_name.get(
            self._fiscal_year_var.get()
        )

    def _open(self) -> None:
        """Erzeugt den Anwendungskontext."""

        company = self._selected_company()
        fiscal_year = self._selected_fiscal_year()

        if (
            company is None
            or fiscal_year is None
        ):
            return

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.destroy()
        
    def _create_new_company(self) -> None:
        """Öffnet den Dialog zum Anlegen einer Buchhaltung."""

        dialog = NewCompanyDialog(
            self,
            repository=self._repository,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        self.result = dialog.result
        self.destroy()
  
    def _create_new_fiscal_year(self) -> None:
        """Legt für das ausgewählte Unternehmen ein Geschäftsjahr an."""

        company = self._selected_company()

        if company is None:
            return

        dialog = NewFiscalYearDialog(
            self,
            repository=self._repository,
            company=company,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        self._load_fiscal_years(
            company
        )

        display_name = dialog.result.display_name

        self._fiscal_year_var.set(
            display_name
        )
    