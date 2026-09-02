"""Dialog zum Anlegen eines neuen Geschäftsjahres."""

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


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
        self.requested_opening_source: FiscalYear | None = None

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
        self._start_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_date_var(
                self._start_date_var
            ),
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

        self._end_date_entry = ttk.Entry(
            form,
            textvariable=self._end_date_var,
            width=16,
        )
        self._end_date_entry.grid(
            row=1,
            column=1,
            sticky="w",
            pady=8,
        )
        self._end_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_date_var(
                self._end_date_var
            ),
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
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(
            value
        )

    def _find_immediate_predecessor(
        self,
        fiscal_year: FiscalYear,
    ):
        """Liefert das unmittelbar vorhergehende Geschäftsjahr."""

        managed_fiscal_years = (
            self._repository.get_managed_fiscal_years(
                self._company.company_id
            )
        )

        expected_end_date = (
            fiscal_year.start_date - timedelta(days=1)
        )

        return next(
            (
                managed
                for managed in managed_fiscal_years
                if (
                    managed.fiscal_year.end_date
                    == expected_end_date
                )
            ),
            None,
        )

    def _confirm_opening_transfer(
        self,
        fiscal_year: FiscalYear,
    ) -> bool:
        """Fragt nach einer möglichen Saldenübernahme."""

        predecessor = self._find_immediate_predecessor(
            fiscal_year
        )

        if predecessor is None:
            self.requested_opening_source = None
            return True

        source_fiscal_year = predecessor.fiscal_year

        if not predecessor.is_closed:
            create_without_transfer = (
                messagebox.askokcancel(
                    "Vorjahr noch nicht abgeschlossen",
                    (
                        "Das unmittelbar vorhergehende "
                        "Geschäftsjahr "
                        f"{source_fiscal_year.display_name} "
                        "ist noch nicht abgeschlossen.\n\n"
                        "Eine Übernahme der Vorjahressalden "
                        "ist deshalb derzeit nicht möglich.\n\n"
                        "Soll das neue Geschäftsjahr trotzdem "
                        "ohne Saldenübernahme angelegt werden?"
                    ),
                    parent=self,
                )
            )

            if not create_without_transfer:
                return False

            self.requested_opening_source = None
            return True

        decision = messagebox.askyesnocancel(
            "Vorjahressalden übernehmen",
            (
                "Das abgeschlossene Geschäftsjahr "
                f"{source_fiscal_year.display_name} "
                "ist das unmittelbare Vorjahr.\n\n"
                "Sollen dessen Schlussbestände als "
                "Eröffnungswerte in das neue Geschäftsjahr "
                "übernommen werden?\n\n"
                "Ja = Vorjahressalden übernehmen\n"
                "Nein = ohne Saldenübernahme anlegen\n"
                "Abbrechen = Geschäftsjahr nicht anlegen"
            ),
            parent=self,
        )

        if decision is None:
            return False

        if decision:
            self.requested_opening_source = (
                source_fiscal_year
            )
        else:
            self.requested_opening_source = None

        return True

    def _create_fiscal_year(self) -> None:
        """Erzeugt und speichert das Geschäftsjahr."""

        try:
            start_date = self._parse_date(
                self._start_date_var.get()
            )
            end_date = self._parse_date(
                self._end_date_var.get()
            )

            self._start_date_var.set(
                start_date.strftime("%d.%m.%Y")
            )
            self._end_date_var.set(
                end_date.strftime("%d.%m.%Y")
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            if not self._confirm_opening_transfer(
                fiscal_year
            ):
                return

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
