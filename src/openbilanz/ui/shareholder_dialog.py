"""Dialoge zur Pflege der Gesellschafterdaten."""

import tkinter as tk
from tkinter import messagebox, ttk
from uuid import UUID

from openbilanz.domain.shareholder import Shareholder
from openbilanz.services.fiscal_year_workspace import (
    FiscalYearWorkspace,
)
from openbilanz.ui.company_master_data_dialog import (
    FEDERAL_STATE_CODES,
    FEDERAL_STATE_LABELS,
    FEDERAL_STATES,
)

LEGAL_STATUSES = (
    ("NPP", "Natürliche Person"),
    ("NPB", "Juristische Person"),
)

LEGAL_STATUS_LABELS = {
    code: label
    for code, label in LEGAL_STATUSES
}

LEGAL_STATUS_CODES = {
    label: code
    for code, label in LEGAL_STATUSES
}


class ShareholdersDialog(tk.Toplevel):
    """Verwaltet die Gesellschafter eines Unternehmens."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        workspace: FiscalYearWorkspace,
    ) -> None:
        super().__init__(parent)

        self._workspace = workspace
        self._shareholders: dict[
            UUID,
            Shareholder,
        ] = {}

        self.title(
            "SimpleOB – Gesellschafter"
        )
        self.geometry("980x520")
        self.minsize(850, 450)

        self.transient(parent)
        self.grab_set()

        self._create_ui()
        self._reload()

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
            text="Gesellschafter",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=self._workspace.context.company.name,
        ).pack(
            anchor="w",
            pady=(4, 18),
        )

        columns = (
            "number",
            "name",
            "first_name",
            "legal_status",
            "share",
        )

        self._tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self._tree.heading(
            "number",
            text="Nr.",
        )
        self._tree.heading(
            "name",
            text="Name",
        )
        self._tree.heading(
            "first_name",
            text="Vorname",
        )
        self._tree.heading(
            "legal_status",
            text="Rechtsstatus",
        )
        self._tree.heading(
            "share",
            text="Anteil",
        )

        self._tree.column(
            "number",
            width=70,
            anchor="w",
            stretch=False,
        )
        self._tree.column(
            "name",
            width=220,
            anchor="w",
        )
        self._tree.column(
            "first_name",
            width=180,
            anchor="w",
        )
        self._tree.column(
            "legal_status",
            width=180,
            anchor="w",
        )
        self._tree.column(
            "share",
            width=100,
            anchor="center",
            stretch=False,
        )

        self._tree.pack(
            fill="both",
            expand=True,
        )

        self._tree.bind(
            "<Double-1>",
            self._on_double_click,
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
            text="Hinzufügen",
            command=self._add,
        ).pack(
            side="left",
        )

        ttk.Button(
            buttons,
            text="Bearbeiten",
            command=self._edit,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Löschen",
            command=self._delete,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            buttons,
            text="Schließen",
            command=self.destroy,
        ).pack(
            side="right",
        )

    def _reload(self) -> None:
        """Lädt die Gesellschafter neu."""

        try:
            shareholders = (
                self._workspace.list_shareholders()
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror(
                "Gesellschafter",
                str(exc),
                parent=self,
            )
            return

        self._shareholders = {
            shareholder.shareholder_id: shareholder
            for shareholder in shareholders
        }

        for item in self._tree.get_children():
            self._tree.delete(item)

        for shareholder in shareholders:
            self._tree.insert(
                "",
                "end",
                iid=str(
                    shareholder.shareholder_id
                ),
                values=(
                    shareholder.shareholder_number,
                    shareholder.name,
                    shareholder.first_name,
                    LEGAL_STATUS_LABELS.get(
                        shareholder.legal_status,
                        shareholder.legal_status,
                    ),
                    (
                        f"{shareholder.share_numerator}"
                        f"/{shareholder.share_denominator}"
                    ),
                ),
            )

    def _selected_shareholder(
        self,
    ) -> Shareholder | None:
        """Liefert den ausgewählten Gesellschafter."""

        selection = self._tree.selection()

        if not selection:
            return None

        try:
            shareholder_id = UUID(
                selection[0]
            )
        except ValueError:
            return None

        return self._shareholders.get(
            shareholder_id
        )

    def _add(self) -> None:
        """Legt einen neuen Gesellschafter an."""

        dialog = ShareholderEditDialog(
            self,
            company_id=(
                self._workspace.context
                .company.company_id
            ),
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.add_shareholder(
                dialog.result
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror(
                "Gesellschafter",
                str(exc),
                parent=self,
            )
            return

        self._reload()

    def _edit(self) -> None:
        """Bearbeitet den ausgewählten Gesellschafter."""

        shareholder = (
            self._selected_shareholder()
        )

        if shareholder is None:
            messagebox.showinfo(
                "Gesellschafter",
                (
                    "Bitte wählen Sie zuerst "
                    "einen Gesellschafter aus."
                ),
                parent=self,
            )
            return

        dialog = ShareholderEditDialog(
            self,
            company_id=(
                self._workspace.context
                .company.company_id
            ),
            shareholder=shareholder,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.update_shareholder(
                dialog.result
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror(
                "Gesellschafter",
                str(exc),
                parent=self,
            )
            return

        self._reload()

    def _delete(self) -> None:
        """Löscht den ausgewählten Gesellschafter."""

        shareholder = (
            self._selected_shareholder()
        )

        if shareholder is None:
            messagebox.showinfo(
                "Gesellschafter",
                (
                    "Bitte wählen Sie zuerst "
                    "einen Gesellschafter aus."
                ),
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Gesellschafter löschen",
            (
                "Soll der Gesellschafter "
                f'"{self._display_name(shareholder)}" '
                "wirklich gelöscht werden?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            self._workspace.delete_shareholder(
                shareholder.shareholder_id
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showerror(
                "Gesellschafter",
                str(exc),
                parent=self,
            )
            return

        self._reload()

    def _on_double_click(
        self,
        _event: tk.Event,
    ) -> None:
        """Öffnet den ausgewählten Eintrag zur Bearbeitung."""

        if self._selected_shareholder() is not None:
            self._edit()

    @staticmethod
    def _display_name(
        shareholder: Shareholder,
    ) -> str:
        """Liefert einen lesbaren Gesellschafternamen."""

        if shareholder.first_name:
            return (
                f"{shareholder.first_name} "
                f"{shareholder.name}"
            )

        return shareholder.name


class ShareholderEditDialog(tk.Toplevel):
    """Bearbeitet einen einzelnen Gesellschafter."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        company_id: UUID,
        shareholder: Shareholder | None = None,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self._shareholder = shareholder
        self.result: Shareholder | None = None

        self.title(
            "SimpleOB – Gesellschafter"
        )
        self.geometry("620x650")
        self.minsize(560, 600)

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

        heading = (
            "Gesellschafter bearbeiten"
            if self._shareholder is not None
            else "Gesellschafter hinzufügen"
        )

        ttk.Label(
            container,
            text=heading,
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=(
                "* Pflichtfeld für die E-Bilanz"
            ),
        ).pack(
            anchor="w",
            pady=(4, 18),
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

        self._number_var = tk.StringVar()
        self._name_var = tk.StringVar()
        self._first_name_var = tk.StringVar()
        self._legal_status_var = tk.StringVar()
        self._numerator_var = tk.StringVar()
        self._denominator_var = tk.StringVar()
        self._tax_number_var = tk.StringVar()
        self._tax_number_federal_state_var = (
            tk.StringVar()
        )
        self._tax_id_var = tk.StringVar()
        self._wid_var = tk.StringVar()

        fields_before_federal_state = (
            (
                "Gesellschafter-Nr. *",
                self._number_var,
            ),
            (
                "Name *",
                self._name_var,
            ),
            (
                "Vorname",
                self._first_name_var,
            ),
            (
                "Anteil Zähler *",
                self._numerator_var,
            ),
            (
                "Anteil Nenner *",
                self._denominator_var,
            ),
            (
                "Steuernummer",
                self._tax_number_var,
            ),
        )

        for row, (
            label,
            variable,
        ) in enumerate(
            fields_before_federal_state
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

        federal_state_row = len(
            fields_before_federal_state
        )

        ttk.Label(
            form,
            text="Bundesland der Steuernummer",
        ).grid(
            row=federal_state_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._tax_number_federal_state_box = (
            ttk.Combobox(
                form,
                textvariable=(
                    self._tax_number_federal_state_var
                ),
                values=tuple(
                    name
                    for _, name in FEDERAL_STATES
                ),
                state="readonly",
            )
        )

        self._tax_number_federal_state_box.grid(
            row=federal_state_row,
            column=1,
            sticky="ew",
            pady=6,
        )

        fields_after_federal_state = (
            (
                "Steuer-ID",
                self._tax_id_var,
            ),
            (
                "Wirtschafts-ID",
                self._wid_var,
            ),
        )

        for offset, (
            label,
            variable,
        ) in enumerate(
            fields_after_federal_state,
            start=1,
        ):
            row = federal_state_row + offset

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

        legal_status_row = (
            federal_state_row
            + len(fields_after_federal_state)
            + 1
        )

        ttk.Label(
            form,
            text="Rechtsstatus *",
        ).grid(
            row=legal_status_row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._legal_status_box = ttk.Combobox(
            form,
            textvariable=(
                self._legal_status_var
            ),
            values=tuple(
                label
                for _, label in LEGAL_STATUSES
            ),
            state="readonly",
        )

        self._legal_status_box.grid(
            row=legal_status_row,
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
        """Übernimmt vorhandene Gesellschafterdaten."""

        if self._shareholder is None:
            self._legal_status_var.set(
                LEGAL_STATUS_LABELS["NPP"]
            )
            self._numerator_var.set("1")
            self._denominator_var.set("1")
            return

        self._number_var.set(
            self._shareholder.shareholder_number
        )
        self._name_var.set(
            self._shareholder.name
        )
        self._first_name_var.set(
            self._shareholder.first_name
        )
        self._legal_status_var.set(
            LEGAL_STATUS_LABELS.get(
                self._shareholder.legal_status,
                "",
            )
        )
        self._numerator_var.set(
            self._shareholder.share_numerator
        )
        self._denominator_var.set(
            self._shareholder.share_denominator
        )
        self._tax_number_var.set(
            self._shareholder.tax_number
        )
        self._tax_number_federal_state_var.set(
            FEDERAL_STATE_LABELS.get(
                self._shareholder.tax_number_federal_state,
                "",
            )
        )
        self._tax_id_var.set(
            self._shareholder.tax_id
        )
        self._wid_var.set(
            self._shareholder.wid
        )

    def _save(self) -> None:
        """Erzeugt den eingegebenen Gesellschafter."""

        legal_status = LEGAL_STATUS_CODES.get(
            self._value(
                self._legal_status_var
            ),
            "",
        )

        tax_number_federal_state = (
            FEDERAL_STATE_CODES.get(
                self._value(
                    self._tax_number_federal_state_var
                ),
                "",
            )
        )

        try:
            values = {
                "company_id": self._company_id,
                "shareholder_number": self._value(
                    self._number_var
                ),
                "name": self._value(
                    self._name_var
                ),
                "first_name": self._value(
                    self._first_name_var
                ),
                "legal_status": legal_status,
                "share_numerator": self._value(
                    self._numerator_var
                ),
                "share_denominator": self._value(
                    self._denominator_var
                ),
                "tax_number": self._value(
                    self._tax_number_var
                ),
                "tax_number_federal_state": (
                    tax_number_federal_state
                ),
                "tax_id": self._value(
                    self._tax_id_var
                ),
                "wid": self._value(
                    self._wid_var
                ),
            }

            if self._shareholder is not None:
                shareholder = Shareholder(
                    shareholder_id=(
                        self._shareholder.shareholder_id
                    ),
                    **values,
                )
            else:
                shareholder = Shareholder(
                    **values,
                )

        except (TypeError, ValueError) as exc:
            messagebox.showerror(
                "Ungültige Gesellschafterdaten",
                str(exc),
                parent=self,
            )
            return

        self.result = shareholder
        self.destroy()

    @staticmethod
    def _value(
        variable: tk.StringVar,
    ) -> str:
        """Liefert einen bereinigten Eingabewert."""

        return variable.get().strip()
