"""Dialog zur E-Bilanz-Taxonomiezuordnung eines Kontos."""

import tkinter as tk
from tkinter import ttk


class EBilanzAccountMappingDialog(tk.Toplevel):
    """Bearbeitet die Taxonomiezuordnung eines einzelnen Kontos."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        account_number: str,
        account_name: str,
        choices: tuple[tuple[str, str], ...],
        current_concept_name: str | None,
    ) -> None:
        super().__init__(
            parent
        )

        self.title(
            f"E-Bilanz-Zuordnung – Konto {account_number}"
        )
        self.resizable(
            True,
            False,
        )
        self.transient(
            parent
        )
        self.grab_set()

        self.result: str | None = current_concept_name
        self.saved = False

        self._choices = choices
        self._concept_by_label = {
            label: concept_name
            for concept_name, label in choices
        }

        self._label_by_concept = {
            concept_name: label
            for concept_name, label in choices
        }

        content = ttk.Frame(
            self,
            padding=16,
        )
        content.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            content,
            text="Konto:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            content,
            text=f"{account_number} – {account_name}",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(12, 0),
        )

        ttk.Label(
            content,
            text="Taxonomie 6.9:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(16, 0),
        )

        current_label = ""

        if current_concept_name is not None:
            current_label = self._label_by_concept.get(
                current_concept_name,
                "",
            )

        self._selection = tk.StringVar(
            value=current_label
        )

        self._combobox = ttk.Combobox(
            content,
            textvariable=self._selection,
            values=tuple(
                label
                for _, label in choices
            ),
            state="readonly",
            width=70,
        )
        self._combobox.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=(16, 0),
        )

        content.columnconfigure(
            1,
            weight=1,
        )

        button_frame = ttk.Frame(
            content
        )
        button_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 0),
        )

        ttk.Button(
            button_frame,
            text="Zuordnung entfernen",
            command=self._remove,
        ).pack(
            side="left",
        )

        ttk.Button(
            button_frame,
            text="Speichern",
            command=self._save,
        ).pack(
            side="right",
        )

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
            padx=(0, 8),
        )

        self.protocol(
            "WM_DELETE_WINDOW",
            self.destroy,
        )

        self.update_idletasks()

        self.minsize(
            620,
            self.winfo_reqheight(),
        )

        self._combobox.focus_set()

    def _save(self) -> None:
        """Übernimmt die ausgewählte Taxonomiezuordnung."""

        label = self._selection.get()

        concept_name = self._concept_by_label.get(
            label
        )

        if concept_name is None:
            return

        self.result = concept_name
        self.saved = True
        self.destroy()

    def _remove(self) -> None:
        """Entfernt die vorhandene Taxonomiezuordnung."""

        self.result = None
        self.saved = True
        self.destroy()
